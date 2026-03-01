# Production Hardening

This page summarizes the hardening layer added on top of the FP reference runtime so teams can evaluate production readiness quickly.

## What was hardened

### Runtime invariants

- strict session state-transition validation (`ACTIVE/PAUSED/CLOSING/CLOSED/FAILED`)
- role patch validation rejects empty role sets
- push config schema validation with required fields and URL constraints
- stream backpressure windows isolated per stream

### Integrity and safety

- receipt signatures bind full context (`receipt_id`, `activity_id`, `provider_entity_id`, `meter_records`)
- in-memory stores use defensive deep copies on `put/get/list`
- transport mapping uses stricter parameter checks for required method fields

### Federated collaboration

- entity-owned FP server publication via HTTP JSON-RPC
- well-known server card endpoint (`/.well-known/fp-server.json`)
- directory-based discovery and entity->server resolution
- remote FP client with structured FP error mapping

## Non-toy scenario coverage

Integration suites now include:

- high-volume multi-entity orchestration (50+ activities in one governed session)
- long-running service workflow with replay/resubscribe/ack and economy closeout
- governed market allocation with deny/approve policy transitions, settlement, and disputes
- framework embedding pattern with shared runtime and quickstart entities
- federated publish/discover/connect/collaborate flow over HTTP

See:

- `tests/integration/test_section3_non_toy_workloads.py`
- `tests/integration/test_federation_network.py`

## Operational checks

Recommended gates:

1. `bash scripts/run_tests.sh`
2. `bash scripts/run_examples.sh`
3. `bash scripts/quality_gate.sh`

These commands validate conformance, integration, performance smoke, runnable scenarios, compile checks, and spec validation.

## Current boundaries

FP remains an in-memory-first reference runtime by default. For deployment at larger scale:

- replace in-memory stores with durable backends
- wire real identity/authn/authz infrastructure
- externalize key management for signatures
- deploy directory as a durable, access-controlled service

The current architecture is intentionally small and explicit, so these upgrades can be introduced without semantic drift from the core protocol.
