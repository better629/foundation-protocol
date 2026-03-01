# FP A+ Production Upgrade Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade FP from high-quality reference runtime to A+ internet-operable protocol implementation with production-grade transport, async, security, federation, and conformance.

**Architecture:** Keep FP semantic core minimal and stable while decomposing runtime into composable modules. Build network-facing capabilities around strict contracts: transport abstraction, signed directory cards, async orchestration, and policy/economy evidence integrity. Preserve developer simplicity through decorators, CLI, and schema-validated boundaries.

**Tech Stack:** Python 3.10+, dataclasses, asyncio/anyio, JSON-RPC 2.0, HTTP(S), JWT, Ed25519, mkdocs, pytest.

### Task 1: Establish A+ acceptance criteria and scorecard

**Files:**
- Create: `docs/specs/fp-a-plus-acceptance.md`
- Modify: `README.md`
- Test: `tests/conformance/test_a_plus_acceptance_contract.py`

**Step 1: Write failing acceptance tests**
- Add tests that assert required capabilities exist and are wired:
- transport-backed client available
- async server/client entrypoints available
- signed server card fields available
- token budget enforcement hook available

**Step 2: Run test to verify it fails**
- Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/conformance/test_a_plus_acceptance_contract.py -q`
- Expected: FAIL due to missing APIs.

**Step 3: Write acceptance spec document**
- Define A+ gates: reliability, security, federation, DX, and performance.

**Step 4: Re-run tests**
- Expected: still FAIL (design phase only), preserving TDD order.

### Task 2: Decompose FPServer god-object into module facades

**Files:**
- Create: `src/fp/runtime/modules/graph_module.py`
- Create: `src/fp/runtime/modules/session_module.py`
- Create: `src/fp/runtime/modules/activity_module.py`
- Create: `src/fp/runtime/modules/event_module.py`
- Create: `src/fp/runtime/modules/economy_module.py`
- Create: `src/fp/runtime/modules/governance_module.py`
- Create: `src/fp/runtime/runtime.py`
- Modify: `src/fp/app/server.py`
- Test: `tests/conformance/test_server_facade_parity.py`

**Step 1: Write failing parity tests**
- Ensure old `FPServer` behavior remains equivalent after decomposition.

**Step 2: Run failing subset**
- Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/conformance/test_server_facade_parity.py -q`
- Expected: FAIL.

**Step 3: Minimal implementation**
- Extract modules and make `FPServer` a thin facade/orchestrator.
- Target: `src/fp/app/server.py` under 250 lines.

**Step 4: Re-run subset**
- Expected: PASS.

### Task 3: Replace local-only FPClient with transport-backed client abstraction

**Files:**
- Create: `src/fp/transport/client_base.py`
- Create: `src/fp/transport/client_http_jsonrpc.py`
- Create: `src/fp/transport/client_inproc.py`
- Modify: `src/fp/app/client.py`
- Modify: `src/fp/federation/network.py`
- Test: `tests/unit/test_client_transports.py`
- Test: `tests/integration/test_client_remote_interop.py`

**Step 1: Write failing tests**
- Client should work against in-proc and remote HTTP endpoints via same interface.

**Step 2: Run failing subset**
- Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/unit/test_client_transports.py tests/integration/test_client_remote_interop.py -q`
- Expected: FAIL.

**Step 3: Minimal implementation**
- Introduce `ClientTransport` protocol and refactor `FPClient` to transport-first API.

**Step 4: Re-run subset**
- Expected: PASS.

### Task 4: Add async runtime and async client/server surfaces

**Files:**
- Create: `src/fp/app/async_server.py`
- Create: `src/fp/app/async_client.py`
- Create: `src/fp/runtime/async_activity_engine.py`
- Create: `src/fp/runtime/async_event_engine.py`
- Create: `src/fp/runtime/async_session_engine.py`
- Modify: `src/fp/runtime/dispatch_engine.py`
- Test: `tests/unit/test_async_runtime.py`
- Test: `tests/integration/test_async_end_to_end.py`

**Step 1: Write failing async tests**
- Add async long-running and concurrent activity flow tests.

**Step 2: Run failing subset**
- Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/unit/test_async_runtime.py tests/integration/test_async_end_to_end.py -q`
- Expected: FAIL.

**Step 3: Minimal implementation**
- Add async-compatible engines and async server/client APIs while retaining sync compatibility.

**Step 4: Re-run subset**
- Expected: PASS.

### Task 5: Upgrade decorator DX with schema extraction and validation

**Files:**
- Create: `src/fp/app/schema_introspection.py`
- Modify: `src/fp/app/decorators.py`
- Modify: `src/fp/runtime/dispatch_engine.py`
- Test: `tests/unit/test_operation_schema.py`
- Test: `tests/integration/test_decorator_dx.py`

**Step 1: Write failing tests**
- Annotated operation signatures generate schema, validate params, and produce clear errors.

**Step 2: Run failing subset**
- Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/unit/test_operation_schema.py tests/integration/test_decorator_dx.py -q`
- Expected: FAIL.

**Step 3: Minimal implementation**
- Implement typed parameter extraction and pre-dispatch validation.

**Step 4: Re-run subset**
- Expected: PASS.

### Task 6: Refactor store layer with generic base and real durable backends

**Files:**
- Create: `src/fp/stores/base.py`
- Modify: `src/fp/stores/memory.py`
- Modify: `src/fp/stores/sqlite.py`
- Modify: `src/fp/stores/redis.py`
- Test: `tests/unit/test_store_generic_base.py`
- Test: `tests/integration/test_store_persistence_semantics.py`

**Step 1: Write failing tests**
- Generic store behavior parity tests.
- Persistence tests for sqlite/redis adapters (no in-memory fallback semantics).

**Step 2: Run failing subset**
- Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/unit/test_store_generic_base.py tests/integration/test_store_persistence_semantics.py -q`
- Expected: FAIL.

**Step 3: Minimal implementation**
- Remove store boilerplate through generic base.
- Provide real persistence semantics or explicit adapter stubs behind feature flags.

**Step 4: Re-run subset**
- Expected: PASS.

### Task 7: Security hardening with JWT auth and mTLS support

**Files:**
- Create: `src/fp/security/jwt_auth.py`
- Create: `src/fp/security/mtls.py`
- Modify: `src/fp/security/auth.py`
- Modify: `src/fp/transport/http_publish.py`
- Test: `tests/unit/test_security_jwt.py`
- Test: `tests/integration/test_mtls_handshake.py`

**Step 1: Write failing tests**
- JWT verification success/failure paths.
- mTLS-required endpoint behavior.

**Step 2: Run failing subset**
- Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/unit/test_security_jwt.py tests/integration/test_mtls_handshake.py -q`
- Expected: FAIL.

**Step 3: Minimal implementation**
- Add pluggable JWT authenticator and mTLS transport options.

**Step 4: Re-run subset**
- Expected: PASS.

### Task 8: Upgrade receipt signature to asymmetric verifiability

**Files:**
- Create: `src/fp/security/ed25519.py`
- Modify: `src/fp/economy/receipt.py`
- Test: `tests/unit/test_receipt_asymmetric_signing.py`
- Test: `tests/integration/test_receipt_third_party_verify.py`

**Step 1: Write failing tests**
- Third party can verify receipt without shared secret.

**Step 2: Run failing subset**
- Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/unit/test_receipt_asymmetric_signing.py tests/integration/test_receipt_third_party_verify.py -q`
- Expected: FAIL.

**Step 3: Minimal implementation**
- Add Ed25519 signature and verification support with key refs.
- Keep HMAC path only as legacy compatibility mode.

**Step 4: Re-run subset**
- Expected: PASS.

### Task 9: Implement public-operable FP Directory spec v0.1

**Files:**
- Create: `spec/fp-directory.schema.json`
- Create: `spec/fp-directory-openrpc.json`
- Create: `src/fp/federation/directory_service.py`
- Create: `src/fp/federation/card_signing.py`
- Modify: `src/fp/federation/network.py`
- Test: `tests/conformance/test_directory_conformance.py`
- Test: `tests/integration/test_directory_ttl_health_acl.py`

**Step 1: Write failing tests**
- Signed cards, TTL expiry, heartbeat refresh, health checks, ACL enforcement.

**Step 2: Run failing subset**
- Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/conformance/test_directory_conformance.py tests/integration/test_directory_ttl_health_acl.py -q`
- Expected: FAIL.

**Step 3: Minimal implementation**
- Implement directory lifecycle states and verification path.

**Step 4: Re-run subset**
- Expected: PASS.

### Task 10: Enforce token budget and context-compaction semantics

**Files:**
- Create: `src/fp/runtime/context_compaction.py`
- Modify: `src/fp/app/server.py`
- Modify: `src/fp/runtime/activity_engine.py`
- Test: `tests/conformance/test_token_budget_enforcement.py`
- Test: `tests/integration/test_context_compaction_flow.py`

**Step 1: Write failing tests**
- Session token budget hard limit behavior.
- Over-budget path returns deterministic FP error.

**Step 2: Run failing subset**
- Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/conformance/test_token_budget_enforcement.py tests/integration/test_context_compaction_flow.py -q`
- Expected: FAIL.

**Step 3: Minimal implementation**
- Enforce token limits in runtime path.
- Prefer `result_ref`/digest path over oversized payloads.

**Step 4: Re-run subset**
- Expected: PASS.

### Task 11: Schema-first synchronization pipeline

**Files:**
- Create: `scripts/generate_models_from_spec.py`
- Create: `scripts/check_spec_sync.py`
- Modify: `scripts/validate_specs.py`
- Modify: `.github/workflows/ci.yml`
- Test: `tests/unit/test_spec_sync_pipeline.py`

**Step 1: Write failing tests**
- Spec/model mismatch must fail CI check.

**Step 2: Run failing subset**
- Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/unit/test_spec_sync_pipeline.py -q`
- Expected: FAIL.

**Step 3: Minimal implementation**
- Add one-way generation and deterministic diff checks.

**Step 4: Re-run subset**
- Expected: PASS.

### Task 12: Interop and chaos testing for internet-grade confidence

**Files:**
- Create: `tests/interop/test_mcp_bridge_contract.py`
- Create: `tests/interop/test_a2a_bridge_contract.py`
- Create: `tests/chaos/test_network_partition_recovery.py`
- Create: `tests/perf/test_directory_scale_smoke.py`
- Modify: `scripts/quality_gate.sh`
- Modify: `README.md`
- Modify: `docs/site/production-hardening.md`

**Step 1: Write failing tests**
- Interop contract, partition recovery, and scale smoke tests.

**Step 2: Run failing subset**
- Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/interop tests/chaos tests/perf/test_directory_scale_smoke.py -q`
- Expected: FAIL.

**Step 3: Minimal implementation**
- Build missing bridge contracts and recovery behaviors.

**Step 4: Re-run subset**
- Expected: PASS.

### Task 13: CLI and operational ergonomics

**Files:**
- Create: `src/fp/cli.py`
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `docs/site/getting-started.md`
- Test: `tests/integration/test_cli_serve.py`

**Step 1: Write failing tests**
- `fp serve` and `fp doctor` commands behavior.

**Step 2: Run failing subset**
- Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/integration/test_cli_serve.py -q`
- Expected: FAIL.

**Step 3: Minimal implementation**
- Add CLI entrypoint for one-command startup and diagnostics.

**Step 4: Re-run subset**
- Expected: PASS.

### Task 14: Final verification and release criteria

**Files:**
- Modify: `docs/site/release-readiness.md`
- Modify: `docs/site/index.md`
- Modify: `scripts/quality_gate.sh`

**Step 1: Run full verification**
- Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest -q`
- Run: `PYTHON_CMD=/opt/anaconda3/envs/aeiva/bin/python bash scripts/run_examples.sh`
- Run: `/opt/anaconda3/envs/aeiva/bin/python -m mkdocs build -q`
- Run: `/opt/anaconda3/envs/aeiva/bin/python scripts/validate_specs.py`

**Step 2: Release checklist**
- Ensure all A+ acceptance gates are green.
- Ensure docs include architecture and operational playbooks.

**Step 3: Final commit**
- Commit in logically scoped batches per task.
