# Foundation Protocol (FP) - Python Reference Runtime

FP is a graph-first control plane for multi-entity AI systems.

This repository contains a production-oriented reference implementation of FP in Python, with explicit runtime semantics for identity, collaboration, policy, provenance, audit, and economy.

## What FP gives you

- Unified object model for entities, organizations, memberships, sessions, activities, and events
- Multi-party collaboration by default (participants + roles + policy + budget)
- Built-in policy hooks and provenance records (not bolt-on logging)
- Ledger-agnostic metering/receipt/settlement/dispute primitives
- Stream semantics with replay/resubscribe/ack and backpressure safety
- Token and cost observability for latency/cost-sensitive applications

## Current implementation scope (`v0.1.0`)

### Runtime engines

- `SessionEngine`: session lifecycle and participant/role coordination
- `ActivityEngine`: canonical activity state machine
- `EventEngine`: publish/stream/replay/resubscribe/ack
- `DispatchEngine`: operation handler registration and invocation
- `IdempotencyGuard`: fingerprinted idempotency key protection

### Protocol, graph, and governance

- Canonical FP objects in `fp.protocol`
- Graph semantics in `fp.graph`
- Policy hooks: `PRE_INVOKE`, `PRE_ROLE_CHANGE`, `PRE_SETTLE`, `POST_EVENT_AUDIT`
- Provenance recording for decisions and critical actions

### Economy and observability

- Meter records, receipts, settlements, disputes
- Token usage and cost estimation per activity
- Audit bundle export for session-level evidence packaging

## Installation

### Runtime only

```bash
python3 -m pip install -e .
```

### Development + docs

```bash
python3 -m pip install -e ".[dev,docs]"
```

## Quick start

```python
from fp.app import FPServer, make_default_entity
from fp.protocol import EntityKind

server = FPServer(server_entity_id="fp:system:runtime")

# Register entities
server.register_entity(make_default_entity("fp:agent:planner", EntityKind.AGENT))
server.register_entity(make_default_entity("fp:tool:weather", EntityKind.TOOL))

# Create collaboration session
session = server.sessions_create(
    participants={"fp:agent:planner", "fp:tool:weather"},
    roles={
        "fp:agent:planner": {"coordinator"},
        "fp:tool:weather": {"provider"},
    },
    policy_ref="policy:trip-planning",
)

# Register operation handler
server.register_operation(
    "weather.lookup",
    lambda payload: {"city": payload["city"], "temp_c": 23},
)

# Start activity
activity = server.activities_start(
    session_id=session.session_id,
    owner_entity_id="fp:tool:weather",
    initiator_entity_id="fp:agent:planner",
    operation="weather.lookup",
    input_payload={"city": "San Francisco"},
    idempotency_key="idem-weather-001",
)

print(activity.state.value)  # completed

# Consume events
stream = server.events_stream(session_id=session.session_id)
events = server.events_read(stream_id=stream["stream_id"], limit=100)
server.events_ack(stream_id=stream["stream_id"], event_ids=[e.event_id for e in events])
```

## How different systems embed FP

FP is designed as a thin control plane, so existing stacks can embed it without rewrites.

### 1) Existing agent framework (planner/executor stack)

- Keep your current planner and memory stack unchanged
- Use FP as the execution coordination layer
- Map framework task runs to FP `Activity`
- Use FP `Session` to model multi-agent collaboration and governance

Typical mapping:

- framework run context -> FP `Session`
- tool call / sub-agent call -> FP `Activity`
- callback/event bus update -> FP `FPEvent`

### 2) LLM provider or model gateway

- Register model-serving endpoint as `EntityKind.TOOL` or `EntityKind.SERVICE`
- Expose model inference as operations (`llm.generate`, `llm.embed`, etc.)
- Return compact result payloads and large outputs by reference (`result_ref`)

### 3) Tool/resource platform

- Represent each tool or resource provider as a distinct FP entity
- Use policy hooks for permission checks before high-risk invocations
- Emit receipts/settlements for billable usage and downstream audit

### 4) Enterprise service integration

- Keep existing service APIs and business logic
- Wrap service calls in FP operations and route through `DispatchEngine`
- Use provenance and audit bundle export for compliance reporting

## Token efficiency and latency strategy

FP runtime defaults are tuned to reduce unnecessary token and transport overhead:

- Progressive disclosure: exchange compact summaries first
- Reference-first payloads: large artifacts via refs instead of repeated inline payloads
- Delta-friendly eventing: push changed state, not full snapshots
- Idempotent retries: avoid duplicate expensive executions
- Backpressure windows: prevent uncontrolled stream fanout

## Reliability and safety guarantees

- Strict activity transition validation
- Session update/join/leave guards for terminal states
- Idempotency key conflict detection via request fingerprinting
- Deterministic schema hash generation for registry stability
- JSON-safe audit export (datetime-safe serialization)

## Repository layout

```text
src/fp/
  quickstart/      # one-screen integration APIs
  app/             # server/client composition layer
  protocol/        # canonical FP objects, methods, errors
  graph/           # entity/org/membership/relationship model
  runtime/         # session/activity/event/dispatch/idempotency engines
  economy/         # meter/receipt/settlement/dispute
  adapters/        # framework integration contract
  transport/       # inproc/stdio/http/sse/websocket bindings
  stores/          # interfaces + memory/sqlite/redis adapters
  policy/          # policy hooks and decisions
  security/        # auth/authz/signature helpers
  observability/   # trace/metrics/token/cost/audit export
  profiles/        # profile presets
  registry/        # schema/event/pattern registries

spec/
  fp-core.schema.json
  fp-openrpc.json

tests/
  integration/     # section-3 aligned scenarios
  conformance/     # protocol/runtime invariants
  unit/            # object and utility tests
  perf/            # smoke-level throughput checks
```

## Testing and quality workflow

Run all tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -q
```

Run spec validation:

```bash
python3 scripts/validate_specs.py
```

Run compile sanity:

```bash
python3 -m compileall -q src tests
```

## Documentation generation (recommended approach)

Best practice for this project is:

1. **MkDocs + Material** for architecture/guides
2. **mkdocstrings** for automatic Python API reference
3. **Strict doc build in CI** to fail on broken links/config

This repo already includes:

- `mkdocs.yml`
- `docs/site/*.md`
- `scripts/serve_docs.sh`
- `scripts/build_docs.sh`

Commands:

```bash
bash scripts/serve_docs.sh   # local preview
bash scripts/build_docs.sh   # static build to site/
```

## Notes for production hardening

The current runtime is intentionally in-memory-first for semantic clarity.
For production:

- Move stores to durable backends
- Add transport auth and stronger identity verification
- Externalize policy engine and signing keys
- Add structured observability exporters and SLO alerts

## License

MIT
