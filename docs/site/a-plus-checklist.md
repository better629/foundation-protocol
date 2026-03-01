# A+ Checklist

Use this page as the concrete release gate for FP A+ hardening.

## Acceptance gates

1. `FPClient` single invocation path
- Pass condition: all public calls route through `ClientTransport`
- Verification: `python -m pytest tests/conformance/test_client_single_path.py -q`

2. Typed async surface
- Pass condition: `AsyncFPServer` public methods expose explicit signatures (no `**kwargs`-only APIs)
- Verification: `python -m pytest tests/unit/test_async_typing_surface.py -q`

3. JSON-safe durable storage
- Pass condition: SQLite persistence uses JSON text (no pickle payloads)
- Verification: `python -m pytest tests/unit/test_sqlite_json_codec.py -q`

4. Remote transport consolidation
- Pass condition: remote federation client reuses shared HTTP JSON-RPC transport
- Verification: `python -m pytest tests/unit/test_remote_client_transport_reuse.py -q`

5. Pagination contract
- Pass condition: deterministic `limit + cursor` semantics in store/runtime/app chain
- Verification:
  - `python -m pytest tests/unit/test_store_pagination_contract.py -q`
  - `python -m pytest tests/integration/test_store_pagination_semantics.py -q`

6. Session-indexed activity listing
- Pass condition: session-scoped activity paging uses indexed path
- Verification: `python -m pytest tests/unit/test_activity_store_session_index.py -q`

7. Activity start orchestration decomposition
- Pass condition: prechecks/idempotency/policy/execution steps covered by dedicated tests
- Verification: `python -m pytest tests/unit/test_activity_orchestrator_steps.py -q`

8. Remote reliability and keep-alive
- Pass condition: retry/backoff/circuit-breaker and keep-alive reuse tested
- Verification: `python -m pytest tests/unit/test_transport_retry_breaker.py tests/integration/test_remote_retry_recovery.py -q`

9. Schema-first sync pipeline
- Pass condition: generated schema-sync artifacts are in sync with specs
- Verification:
  - `python scripts/check_spec_sync.py`
  - `python -m pytest tests/unit/test_spec_sync_pipeline.py -q`

10. End-to-end release gate
- Pass condition: all tests and docs/spec quality checks succeed in one run
- Verification:
  - `bash scripts/quality_gate.sh`
  - `python -m mkdocs build --strict`

## Recommended one-shot verification

```bash
python scripts/check_spec_sync.py
python -m pytest -q
bash scripts/quality_gate.sh
python -m mkdocs build --strict
```

If all commands pass, FP runtime is ready for white-paper-aligned A+ release packaging.
