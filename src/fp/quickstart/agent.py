"""Quickstart Agent API."""

from __future__ import annotations

from typing import Any, Callable

from fp.app import FPServer, make_default_entity
from fp.protocol import EntityKind


class Agent:
    def __init__(self, *, entity_id: str, profile: str = "core_streaming", server: FPServer | None = None) -> None:
        self.entity_id = entity_id
        self.profile = profile
        self.server = server or FPServer()
        self.server.register_entity(make_default_entity(entity_id, EntityKind.AGENT, display_name=entity_id))

    def activity(self, operation: str) -> Callable[[Callable[[dict[str, Any]], Any]], Callable[[dict[str, Any]], Any]]:
        def decorator(fn: Callable[[dict[str, Any]], Any]) -> Callable[[dict[str, Any]], Any]:
            self.server.register_operation(operation, fn)
            return fn

        return decorator

    def start_session(self, *, participants: set[str], roles: dict[str, set[str]], policy_ref: str | None = None):
        return self.server.sessions_create(participants=participants, roles=roles, policy_ref=policy_ref)

    def start_activity(
        self,
        *,
        session_id: str,
        operation: str,
        input_payload: dict[str, Any],
        owner_entity_id: str | None = None,
        auto_execute: bool = True,
    ):
        return self.server.activities_start(
            session_id=session_id,
            owner_entity_id=owner_entity_id or self.entity_id,
            initiator_entity_id=self.entity_id,
            operation=operation,
            input_payload=input_payload,
            auto_execute=auto_execute,
        )

    def serve_http(self, host: str, port: int) -> FPServer:
        # HTTP binding can be attached externally while preserving one-line quickstart UX.
        _ = (host, port)
        return self.server
