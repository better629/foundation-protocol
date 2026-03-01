# FP Production Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Harden FP runtime and test suite to production-grade reliability with stricter protocol correctness, stronger integrity guarantees, and non-toy scenario validation aligned with the white paper.

**Architecture:** Tighten invariants at runtime boundaries (session/activity/event/economy/transport), enforce stricter input semantics, and prevent mutation leaks from storage adapters. Extend tests first (RED), then minimally implement (GREEN), then refactor for clarity while preserving simple embedding APIs.

**Tech Stack:** Python 3.12+, `unittest`/`pytest`, dataclasses, in-memory reference runtime, JSON-RPC mapping layer.

### Task 1: Session lifecycle hardening

**Files:**
- Modify: `tests/conformance/test_core_conformance.py`
- Modify: `src/fp/runtime/session_engine.py`

**Step 1: Write failing tests**
- Add tests for:
  - disallowed session state transitions (e.g., `ACTIVE -> CREATED`)
  - valid transitions (`ACTIVE -> PAUSED -> ACTIVE -> CLOSING -> CLOSED`)
  - role patch rejection for empty role sets
  - preventing updates when session already terminal

**Step 2: Run failing subset**
- Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/conformance/test_core_conformance.py -q`
- Expected: FAIL on new transition assertions.

**Step 3: Minimal implementation**
- Add explicit `_ALLOWED_SESSION_TRANSITIONS`.
- Validate transition legality in `SessionEngine.update` and `SessionEngine.close`.
- Validate non-empty role sets in `roles_patch`.

**Step 4: Re-run subset**
- Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/conformance/test_core_conformance.py -q`
- Expected: PASS.

### Task 2: Event stream safety hardening

**Files:**
- Modify: `tests/conformance/test_core_conformance.py`
- Modify: `src/fp/runtime/backpressure.py`
- Modify: `src/fp/runtime/event_engine.py`

**Step 1: Write failing tests**
- Add multi-stream test proving one stream's configured window must not impact others.
- Add push-config validation tests (required keys, URL scheme, scope shape, auth shape, event_types shape).

**Step 2: Run failing subset**
- Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/conformance/test_core_conformance.py -q`
- Expected: FAIL on new stream/push-config tests.

**Step 3: Minimal implementation**
- Track backpressure windows per stream instead of global scalar.
- Guard push-config mutations under lock and validate shape strictly.

**Step 4: Re-run subset**
- Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/conformance/test_core_conformance.py -q`
- Expected: PASS.

### Task 3: Integrity and store mutation hardening

**Files:**
- Modify: `tests/unit/test_protocol_and_meters.py`
- Modify: `src/fp/economy/receipt.py`
- Modify: `src/fp/stores/memory.py`

**Step 1: Write failing tests**
- Receipt verify should fail if `activity_id`/`provider_entity_id`/`meter_records` are tampered after issue.
- In-memory store `get/list` should return copies; external mutation must not mutate store state.

**Step 2: Run failing subset**
- Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/unit/test_protocol_and_meters.py tests/conformance/test_core_conformance.py -q`
- Expected: FAIL on tamper/mutation tests.

**Step 3: Minimal implementation**
- Canonicalize and sign full receipt context payload.
- Return defensive deep copies in in-memory stores.

**Step 4: Re-run subset**
- Run same command; expected PASS.

### Task 4: JSON-RPC strictness hardening

**Files:**
- Modify: `tests/unit/test_jsonrpc_transport.py`
- Modify: `src/fp/transport/http_jsonrpc.py`

**Step 1: Write failing tests**
- `fp/activities.start` missing/blank `operation` should return `INVALID_PARAMS`.
- `fp/sessions.create` missing/empty participants should reject early.
- push-config method should reject malformed `config`.

**Step 2: Run failing subset**
- Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/unit/test_jsonrpc_transport.py -q`
- Expected: FAIL on new strictness assertions.

**Step 3: Minimal implementation**
- Remove permissive defaults for required method fields.
- Add explicit argument guards in request mapping helpers.

**Step 4: Re-run subset**
- Run same command; expected PASS.

### Task 5: Non-toy white-paper scenario expansion

**Files:**
- Modify: `tests/integration/test_section3_scenarios.py`
- Add: `tests/integration/test_section3_non_toy_workloads.py`

**Step 1: Write tests**
- Add long-running workflow with reconnect/resubscribe and checkpointed completion.
- Add high-volume multi-entity bidding/settlement flow with deterministic ordering assertions.
- Add framework-embedding style scenario via quickstart + adapter contract simulation.

**Step 2: Run integration subset**
- Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/integration -q`
- Expected: PASS after implementation.

### Task 6: Docs and verification

**Files:**
- Modify: `README.md`
- Modify: `docs/site/index.md`
- Modify: `docs/site/getting-started.md`
- Add: `docs/site/production-hardening.md`

**Step 1: Update docs**
- Document hardening guarantees, operational limits, and non-toy scenario coverage.
- Add direct runnable commands and embedding patterns.

**Step 2: Full verification**
- Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest -q`
- Run: `bash scripts/run_examples.sh`
- Run: `bash scripts/quality_gate.sh`
- Expected: all pass.

**Step 3: Final consistency pass**
- Ensure wording aligns with white-paper purpose and avoids unsupported claims.
- Keep API surface minimal/simple.
