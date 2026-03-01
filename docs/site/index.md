# Foundation Protocol (FP)

FP is a graph-first control plane for multi-entity AI systems.

This Python repository provides a reference runtime focused on:

- Unified entity/session/activity/event semantics
- Multi-party collaboration with explicit roles
- Policy + provenance + audit as built-in behavior
- Ledger-agnostic economy primitives
- Token-efficient execution defaults for latency and cost control

Use this site as the source of truth for SDK usage, architecture, and API surface.

## FP in one flow

1. Register entities (`agent`, `tool`, `resource`, `service`, etc.).
2. Create a session with participants, roles, policy, and budget.
3. Start activities and route operations through dispatch handlers.
4. Stream events with replay/resubscribe/ack.
5. Export audit bundles and economy artifacts when needed.

## Project maturity

- Current version: `0.1.0`
- Implementation style: in-memory-first, extension-friendly
- Recommended usage: reference runtime, local integration, protocol validation, and architecture baseline
