"""FP client API."""

from __future__ import annotations

import ssl
from dataclasses import asdict, is_dataclass
from typing import Any

from fp.protocol import ActivityState, EntityKind, SessionBudget
from fp.transport import HTTPJSONRPCClientTransport, InProcessJSONRPCClientTransport
from fp.transport.client_base import ClientTransport


class FPClient:
    def __init__(self, server: Any | None = None, *, transport: ClientTransport | None = None) -> None:
        if server is None and transport is None:
            raise ValueError("server or transport is required")
        self._server = server
        self._transport = transport

    @classmethod
    def from_inproc(cls, server: Any) -> "FPClient":
        return cls(server=None, transport=InProcessJSONRPCClientTransport(server))

    @classmethod
    def from_http_jsonrpc(
        cls,
        rpc_url: str,
        *,
        timeout_seconds: float = 10.0,
        headers: dict[str, str] | None = None,
        ssl_context: ssl.SSLContext | None = None,
    ) -> "FPClient":
        return cls(
            server=None,
            transport=HTTPJSONRPCClientTransport(
                rpc_url,
                timeout_seconds=timeout_seconds,
                headers=headers,
                ssl_context=ssl_context,
            ),
        )

    def _call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        if self._transport is None:
            raise RuntimeError(f"transport call attempted without transport: {method}")
        return self._transport.call(method, params or {})

    def initialize(self, *, supported_versions: list[str], entity_id: str, profile: str | None = None) -> dict[str, Any]:
        profiles = [profile] if profile else []
        if self._transport:
            result = self._call(
                "fp/initialize",
                {
                    "supported_versions": supported_versions,
                    "entity_id": entity_id,
                    "capabilities": {},
                    "supported_profiles": profiles,
                },
            )
            return dict(result or {})
        return self._server.initialize(supported_versions=supported_versions, entity_id=entity_id, capabilities={}, supported_profiles=profiles)

    def ping(self) -> dict[str, Any]:
        if self._transport:
            result = self._call("fp/ping", {})
            return dict(result or {})
        return {"ok": True, "fp_version": getattr(self._server, "fp_version", "unknown")}

    # Entity API
    def register_entity(self, entity):
        if self._transport:
            payload = asdict(entity) if is_dataclass(entity) else entity
            return self._call("fp/entities.register", {"entity": payload})
        return self._server.register_entity(entity)

    def get_entity(self, entity_id: str):
        if self._transport:
            return self._call("fp/entities.get", {"entity_id": entity_id})
        return self._server.get_entity(entity_id)

    # Session API
    def session_create(self, *, participants: set[str], roles: dict[str, set[str]], policy_ref: str | None = None, budget: SessionBudget | None = None):
        if self._transport:
            payload: dict[str, Any] = {
                "participants": sorted(participants),
                "roles": {entity_id: sorted(role_set) for entity_id, role_set in roles.items()},
                "policy_ref": policy_ref,
            }
            if budget is not None:
                payload["budget"] = {
                    "token_limit": budget.token_limit,
                    "spend_limit": None
                    if budget.spend_limit is None
                    else {"currency": budget.spend_limit.currency, "amount": budget.spend_limit.amount},
                }
            return self._call("fp/sessions.create", payload)
        return self._server.sessions_create(participants=participants, roles=roles, policy_ref=policy_ref, budget=budget)

    def session_get(self, session_id: str):
        if self._transport:
            return self._call("fp/sessions.get", {"session_id": session_id})
        return self._server.sessions_get(session_id)

    # Activity API
    def activity_start(
        self,
        *,
        session_id: str,
        owner_entity_id: str,
        initiator_entity_id: str,
        operation: str,
        input_payload: dict[str, Any],
        auto_execute: bool = True,
    ):
        if self._transport:
            return self._call(
                "fp/activities.start",
                {
                    "session_id": session_id,
                    "owner_entity_id": owner_entity_id,
                    "initiator_entity_id": initiator_entity_id,
                    "operation": operation,
                    "input_payload": input_payload,
                    "auto_execute": auto_execute,
                },
            )
        return self._server.activities_start(
            session_id=session_id,
            owner_entity_id=owner_entity_id,
            initiator_entity_id=initiator_entity_id,
            operation=operation,
            input_payload=input_payload,
            auto_execute=auto_execute,
        )

    def activity_update(self, *, activity_id: str, state: ActivityState, status_message: str | None = None, patch: dict[str, Any] | None = None):
        if self._transport:
            return self._call(
                "fp/activities.update",
                {
                    "activity_id": activity_id,
                    "state": state.value,
                    "status_message": status_message,
                    "patch": patch or {},
                },
            )
        return self._server.activities_update(
            activity_id=activity_id,
            state=state,
            status_message=status_message,
            patch=patch,
        )

    def activity_result(self, *, activity_id: str):
        if self._transport:
            return self._call("fp/activities.result", {"activity_id": activity_id})
        return self._server.activities_result(activity_id=activity_id)

    def activity_cancel(self, *, activity_id: str, reason: str | None = None):
        if self._transport:
            return self._call("fp/activities.cancel", {"activity_id": activity_id, "reason": reason})
        return self._server.activities_cancel(activity_id=activity_id, reason=reason)

    # Event API
    def events_stream(self, *, session_id: str, activity_id: str | None = None, from_event_id: str | None = None):
        if self._transport:
            return self._call(
                "fp/events.stream",
                {
                    "session_id": session_id,
                    "activity_id": activity_id,
                    "from_event_id": from_event_id,
                },
            )
        return self._server.events_stream(session_id=session_id, activity_id=activity_id, from_event_id=from_event_id)

    def events_read(self, *, stream_id: str, limit: int = 200):
        if self._transport:
            return self._call("fp/events.read", {"stream_id": stream_id, "limit": limit})
        return self._server.events_read(stream_id=stream_id, limit=limit)

    def events_ack(self, *, stream_id: str, event_ids: list[str]):
        if self._transport:
            return self._call("fp/events.ack", {"stream_id": stream_id, "event_ids": event_ids})
        return self._server.events_ack(stream_id=stream_id, event_ids=event_ids)
