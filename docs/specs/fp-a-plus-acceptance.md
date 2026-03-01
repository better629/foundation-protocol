# FP A+ Acceptance Contract

This document defines the minimum acceptance gates for calling an FP release "A+" production-grade.

## Gate 1: Transport-backed client

- `FPClient` must support transport-based construction for:
- in-process transport
- remote HTTP JSON-RPC transport

Client code must not require direct Python-object coupling to server internals.

## Gate 2: Async runtime surface

- Async API entrypoints must exist for server and client flows.
- Async entrypoints must support initialize and activity/session/event operations.

## Gate 3: Signed, expiring federation card

- `FPServerCard` must include signed identity metadata:
- `sign_alg`
- `key_ref`
- `signature`
- `issued_at`
- `expires_at`
- `ttl_seconds`

## Gate 4: Token budget enforcement hook

- Runtime must expose a token budget enforcement hook callable from activity path.
- Hook must be configurable at server construction or via explicit setter.

## Gate 5: Backward compatibility

- Existing synchronous APIs remain usable for current integrations.
- A+ upgrades must preserve semantic compatibility for protocol objects and error codes.
