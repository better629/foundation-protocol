# FP A+ Final Hardening Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close all remaining production-grade gaps and move FP from A- to A+ without semantic drift from the white paper.

**Architecture:** Keep FP semantic model stable (Entity/Session/Activity/Event/Governance/Economy) while hardening execution internals. Prioritize single-path client semantics, typed async surfaces, storage safety, and operability primitives (retry/pagination/transport consolidation). Avoid large rewrites; ship in verifiable increments.

**Tech Stack:** Python 3.10+, dataclasses, asyncio, sqlite3, JSON-RPC 2.0, pytest, mkdocs.

## Acceptance Gates (A+)

1. `FPClient` has one invocation path (always through `ClientTransport`) with no server bypass branch.
2. `AsyncFPServer` public methods preserve concrete typed signatures (no `**kwargs: Any -> Any` API surface).
3. `SQLiteStoreBundle` no longer uses pickle for persisted payloads.
4. `RemoteFPClient` reuses `HTTPJSONRPCClientTransport` (single HTTP JSON-RPC logic path).
5. Store layer supports pagination (`limit` + `cursor`) on large-list APIs.
6. `activities_start` orchestration is decomposed into testable sub-steps.
7. Network client has built-in bounded retry + backoff + jitter + circuit-breaker.
8. All existing tests + new hardening tests pass in one run.

---

### Task 1: Make FPClient transport-only

**Files:**
- Modify: `src/fp/app/client.py`
- Modify: `src/fp/app/async_client.py`
- Modify: `src/fp/quickstart/client.py`
- Test: `tests/unit/test_client_transports.py`
- Test: `tests/integration/test_client_remote_interop.py`
- Create: `tests/conformance/test_client_single_path.py`

**Step 1: Write failing test**
- Add test asserting `FPClient` initialization without `transport` fails.
- Add test asserting every public API call goes through a fake transport recorder.

**Step 2: Run test to verify it fails**
- Run: `python -m pytest tests/conformance/test_client_single_path.py -q`

**Step 3: Minimal implementation**
- Remove `_server` fallback path and `if self._transport` branches.
- Keep convenience constructors: `from_inproc`, `from_http_jsonrpc`.

**Step 4: Re-run tests**
- Run: `python -m pytest tests/conformance/test_client_single_path.py tests/unit/test_client_transports.py tests/integration/test_client_remote_interop.py -q`

**Step 5: Commit**
- `git commit -m "refactor: make FPClient transport-only"`

---

### Task 2: Give AsyncFPServer explicit typed signatures

**Files:**
- Modify: `src/fp/app/async_server.py`
- Modify: `src/fp/app/async_client.py`
- Test: `tests/unit/test_async_runtime.py`
- Create: `tests/unit/test_async_typing_surface.py`

**Step 1: Write failing test**
- Introspect function signatures and assert required named parameters exist.
- Assert no async API method uses only `**kwargs` in public surface.

**Step 2: Run failing test**
- `python -m pytest tests/unit/test_async_typing_surface.py -q`

**Step 3: Minimal implementation**
- Replace `**kwargs: Any -> Any` with concrete signatures mirroring sync API.
- Keep `asyncio.to_thread` bridge internally for now.

**Step 4: Re-run tests**
- `python -m pytest tests/unit/test_async_typing_surface.py tests/unit/test_async_runtime.py tests/integration/test_async_end_to_end.py -q`

**Step 5: Commit**
- `git commit -m "refactor: type explicit AsyncFPServer API signatures"`

---

### Task 3: Consolidate RemoteFPClient over HTTPJSONRPCClientTransport

**Files:**
- Modify: `src/fp/federation/network.py`
- Modify: `src/fp/transport/client_http_jsonrpc.py`
- Test: `tests/integration/test_client_remote_interop.py`
- Create: `tests/unit/test_remote_client_transport_reuse.py`

**Step 1: Write failing test**
- Assert `RemoteFPClient` delegates to `HTTPJSONRPCClientTransport.call`.

**Step 2: Run failing test**
- `python -m pytest tests/unit/test_remote_client_transport_reuse.py -q`

**Step 3: Minimal implementation**
- Inject/compose transport inside `RemoteFPClient`.
- Remove duplicated error-mapping logic from federation client.

**Step 4: Re-run tests**
- `python -m pytest tests/unit/test_remote_client_transport_reuse.py tests/integration/test_client_remote_interop.py tests/integration/test_federation_network.py -q`

**Step 5: Commit**
- `git commit -m "refactor: deduplicate remote JSON-RPC client logic"`

---

### Task 4: Add retry/backoff/circuit-breaker for remote calls

**Files:**
- Modify: `src/fp/transport/client_http_jsonrpc.py`
- Create: `src/fp/transport/reliability.py`
- Modify: `src/fp/federation/network.py`
- Create: `tests/unit/test_transport_retry_breaker.py`
- Create: `tests/integration/test_remote_retry_recovery.py`

**Step 1: Write failing tests**
- transient `URLError` should retry and then succeed.
- repeated failures should open breaker and fail fast until cooldown.

**Step 2: Run failing subset**
- `python -m pytest tests/unit/test_transport_retry_breaker.py tests/integration/test_remote_retry_recovery.py -q`

**Step 3: Minimal implementation**
- Configurable retries: `max_attempts`, exponential backoff, jitter, retryable-code filter.
- Circuit breaker states: `closed/open/half-open`.

**Step 4: Re-run tests**
- same command, expected pass.

**Step 5: Commit**
- `git commit -m "feat: add retry and circuit-breaker to remote transport"`

---

### Task 5: Replace SQLite pickle with JSON-safe encoding

**Files:**
- Modify: `src/fp/stores/sqlite.py`
- Create: `src/fp/stores/codec.py`
- Modify: `src/fp/transport/http_jsonrpc.py` (reuse canonical serializer if needed)
- Test: `tests/integration/test_store_persistence_semantics.py`
- Create: `tests/unit/test_sqlite_json_codec.py`

**Step 1: Write failing tests**
- verify raw SQLite row values are UTF-8 JSON text, not pickle blobs.
- verify datetime/enum roundtrip remains lossless for protocol objects.

**Step 2: Run failing tests**
- `python -m pytest tests/unit/test_sqlite_json_codec.py tests/integration/test_store_persistence_semantics.py -q`

**Step 3: Minimal implementation**
- Encode dataclass objects to JSON via canonical dict conversion.
- Decode through typed constructors for each model class.
- Add migration policy: fail clearly on legacy non-JSON rows (or one-time converter script).

**Step 4: Re-run tests**
- same command, expected pass.

**Step 5: Commit**
- `git commit -m "refactor: use JSON codec for SQLite persistence"`

---

### Task 6: Add pagination contract to store interfaces and implementations

**Files:**
- Modify: `src/fp/stores/interfaces.py`
- Modify: `src/fp/stores/memory.py`
- Modify: `src/fp/stores/sqlite.py`
- Modify: `src/fp/runtime/*_engine.py` (list consumers)
- Modify: `src/fp/app/server.py`
- Create: `tests/unit/test_store_pagination_contract.py`
- Create: `tests/integration/test_store_pagination_semantics.py`

**Step 1: Write failing tests**
- list APIs support `limit` and `cursor`; cursor advances deterministically.

**Step 2: Run failing tests**
- `python -m pytest tests/unit/test_store_pagination_contract.py tests/integration/test_store_pagination_semantics.py -q`

**Step 3: Minimal implementation**
- add paged list methods while keeping backward-compatible wrappers.
- implement cursor tokens as opaque deterministic strings.

**Step 4: Re-run tests**
- same command.

**Step 5: Commit**
- `git commit -m "feat: add pagination to store and runtime listing APIs"`

---

### Task 7: Optimize activity listing with session index

**Files:**
- Modify: `src/fp/stores/memory.py`
- Modify: `src/fp/stores/sqlite.py`
- Test: `tests/perf/test_event_throughput_smoke.py`
- Create: `tests/unit/test_activity_store_session_index.py`

**Step 1: Write failing test**
- Assert session-scoped list path does not scan all records (behavioral proxy checks).

**Step 2: Run failing test**
- `python -m pytest tests/unit/test_activity_store_session_index.py -q`

**Step 3: Minimal implementation**
- memory: use `InMemoryGroupedKVStore` for activities by `session_id`.
- sqlite: add index `(session_id, activity_id)` and filtered query path.

**Step 4: Re-run tests**
- `python -m pytest tests/unit/test_activity_store_session_index.py tests/perf/test_event_throughput_smoke.py -q`

**Step 5: Commit**
- `git commit -m "perf: index activities by session for scalable listing"`

---

### Task 8: Decompose `activities_start` orchestration

**Files:**
- Modify: `src/fp/app/server.py`
- Create: `src/fp/app/activity_orchestrator.py`
- Test: `tests/conformance/test_core_conformance.py`
- Create: `tests/unit/test_activity_orchestrator_steps.py`

**Step 1: Write failing tests**
- independent tests for each step:
  - participant/session prechecks
  - budget guard
  - idempotency check/store
  - policy gate
  - auto execution + completion/failure event emission

**Step 2: Run failing tests**
- `python -m pytest tests/unit/test_activity_orchestrator_steps.py -q`

**Step 3: Minimal implementation**
- extract helper methods/class; keep FP semantics identical.

**Step 4: Re-run tests**
- `python -m pytest tests/unit/test_activity_orchestrator_steps.py tests/conformance/test_core_conformance.py -q`

**Step 5: Commit**
- `git commit -m "refactor: split activity start orchestration into testable steps"`

---

### Task 9: Schema-first sync pipeline (close the remaining 1/7 gap)

**Files:**
- Create: `scripts/generate_models_from_spec.py`
- Create: `scripts/check_spec_sync.py`
- Modify: `scripts/validate_specs.py`
- Modify: `.github/workflows/ci.yml`
- Create: `tests/unit/test_spec_sync_pipeline.py`

**Step 1: Write failing test**
- introduce intentional mismatch fixture and assert CI check fails.

**Step 2: Run failing test**
- `python -m pytest tests/unit/test_spec_sync_pipeline.py -q`

**Step 3: Minimal implementation**
- deterministic generation/check flow (`spec -> model stubs/hash manifest`).
- CI gate fails on drift.

**Step 4: Re-run tests**
- same command.

**Step 5: Commit**
- `git commit -m "feat: add schema-model sync pipeline and CI guard"`

---

### Task 10: Final verification, docs, and release gate

**Files:**
- Modify: `README.md`
- Modify: `docs/site/production-hardening.md`
- Modify: `docs/site/release-readiness.md`
- Create: `docs/site/a-plus-checklist.md`

**Step 1: Add A+ checklist doc**
- include each acceptance gate and verification command.

**Step 2: Full verification run**
- `python -m pytest -q`
- `bash scripts/quality_gate.sh`
- `python -m mkdocs build --strict`

**Step 3: Publish validation evidence**
- capture command outputs and final gate table.

**Step 4: Commit**
- `git commit -m "docs: publish A+ hardening checklist and verification evidence"`

---

## Delivery strategy

1. Execute Tasks 1-4 first (P0), then freeze API for one pass of regression tests.
2. Execute Tasks 5-8 (P1) in small commits; no mixed refactor+feature changes in one commit.
3. Execute Task 9 to close schema-first gap.
4. Execute Task 10 and release.

## Definition of Done

- All A+ acceptance gates satisfied.
- Full test suite green.
- Docs site updated with explicit A+ checklist and operational guidance.
- No semantic regressions vs FP white-paper core model.
