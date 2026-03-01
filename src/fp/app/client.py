"""FP client API."""

from __future__ import annotations

import ssl
from dataclasses import asdict, is_dataclass
from typing import Any

from fp.protocol import ActivityState, EntityKind, SessionBudget
from fp.transport.reliability import CircuitBreaker, RetryPolicy
from fp.transport import HTTPJSONRPCClientTransport, InProcessJSONRPCClientTransport
from fp.transport.client_base import ClientTransport


class FPClient:
    def __init__(self, *, transport: ClientTransport) -> None:
        self._transport = transport

    @classmethod
    def from_inproc(cls, server: Any) -> "FPClient":
        return cls(transport=InProcessJSONRPCClientTransport(server))

    @classmethod
    def from_http_jsonrpc(
        cls,
        rpc_url: str,
        *,
        timeout_seconds: float = 10.0,
        headers: dict[str, str] | None = None,
        ssl_context: ssl.SSLContext | None = None,
        retry_policy: RetryPolicy | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        keep_alive: bool = True,
    ) -> "FPClient":
        return cls(
            transport=HTTPJSONRPCClientTransport(
                rpc_url,
                timeout_seconds=timeout_seconds,
                headers=headers,
                ssl_context=ssl_context,
                retry_policy=retry_policy,
                circuit_breaker=circuit_breaker,
                keep_alive=keep_alive,
            ),
        )

    def _call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        return self._transport.call(method, params or {})

    def initialize(self, *, supported_versions: list[str], entity_id: str, profile: str | None = None) -> dict[str, Any]:
        profiles = [profile] if profile else []
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

    def ping(self) -> dict[str, Any]:
        result = self._call("fp/ping", {})
        return dict(result or {})

    # Entity API
    def register_entity(self, entity):
        payload = asdict(entity) if is_dataclass(entity) else entity
        return self._call("fp/entities.register", {"entity": payload})

    def get_entity(self, entity_id: str):
        return self._call("fp/entities.get", {"entity_id": entity_id})

    def entities_list(self):
        return self._call("fp/entities.list", {})

    def entities_list_page(self, *, limit: int = 100, cursor: str | None = None):
        return self._call("fp/entities.listPage", {"limit": limit, "cursor": cursor})

    # Session API
    def session_create(
        self,
        *,
        participants: set[str],
        roles: dict[str, set[str]],
        policy_ref: str | None = None,
        budget: SessionBudget | None = None,
        session_id: str | None = None,
    ):
        payload: dict[str, Any] = {
            "participants": sorted(participants),
            "roles": {entity_id: sorted(role_set) for entity_id, role_set in roles.items()},
            "policy_ref": policy_ref,
            "session_id": session_id,
        }
        if budget is not None:
            payload["budget"] = {
                "token_limit": budget.token_limit,
                "spend_limit": None
                if budget.spend_limit is None
                else {"currency": budget.spend_limit.currency, "amount": budget.spend_limit.amount},
            }
        return self._call("fp/sessions.create", payload)

    def session_get(self, session_id: str):
        return self._call("fp/sessions.get", {"session_id": session_id})

    def session_list(self):
        return self._call("fp/sessions.list", {})

    def session_list_page(self, *, limit: int = 100, cursor: str | None = None):
        return self._call("fp/sessions.listPage", {"limit": limit, "cursor": cursor})

    # Activity API
    def activity_start(
        self,
        *,
        session_id: str,
        owner_entity_id: str,
        initiator_entity_id: str,
        operation: str,
        input_payload: dict[str, Any],
        activity_id: str | None = None,
        idempotency_key: str | None = None,
        auto_execute: bool = True,
    ):
        return self._call(
            "fp/activities.start",
            {
                "session_id": session_id,
                "owner_entity_id": owner_entity_id,
                "initiator_entity_id": initiator_entity_id,
                "operation": operation,
                "input_payload": input_payload,
                "activity_id": activity_id,
                "idempotency_key": idempotency_key,
                "auto_execute": auto_execute,
            },
        )

    def activity_update(self, *, activity_id: str, state: ActivityState, status_message: str | None = None, patch: dict[str, Any] | None = None):
        return self._call(
            "fp/activities.update",
            {
                "activity_id": activity_id,
                "state": state.value,
                "status_message": status_message,
                "patch": patch or {},
            },
        )

    def activity_result(self, *, activity_id: str):
        return self._call("fp/activities.result", {"activity_id": activity_id})

    def activity_list(
        self,
        *,
        session_id: str | None = None,
        state: str | None = None,
        owner_entity_id: str | None = None,
    ):
        return self._call(
            "fp/activities.list",
            {
                "session_id": session_id,
                "state": state,
                "owner_entity_id": owner_entity_id,
            },
        )

    def activity_list_page(
        self,
        *,
        session_id: str | None = None,
        state: str | None = None,
        owner_entity_id: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ):
        return self._call(
            "fp/activities.listPage",
            {
                "session_id": session_id,
                "state": state,
                "owner_entity_id": owner_entity_id,
                "limit": limit,
                "cursor": cursor,
            },
        )

    def activity_cancel(self, *, activity_id: str, reason: str | None = None):
        return self._call("fp/activities.cancel", {"activity_id": activity_id, "reason": reason})

    # Event API
    def events_stream(self, *, session_id: str, activity_id: str | None = None, from_event_id: str | None = None):
        return self._call(
            "fp/events.stream",
            {
                "session_id": session_id,
                "activity_id": activity_id,
                "from_event_id": from_event_id,
            },
        )

    def events_read(self, *, stream_id: str, limit: int = 200):
        return self._call("fp/events.read", {"stream_id": stream_id, "limit": limit})

    def events_ack(self, *, stream_id: str, event_ids: list[str]):
        return self._call("fp/events.ack", {"stream_id": stream_id, "event_ids": event_ids})

    # Economy and audit APIs
    def receipts_list_page(self, *, limit: int = 100, cursor: str | None = None):
        return self._call("fp/receipts.listPage", {"limit": limit, "cursor": cursor})

    def settlements_list_page(self, *, limit: int = 100, cursor: str | None = None):
        return self._call("fp/settlements.listPage", {"limit": limit, "cursor": cursor})

    def disputes_list_page(self, *, limit: int = 100, cursor: str | None = None):
        return self._call("fp/disputes.listPage", {"limit": limit, "cursor": cursor})

    def provenance_list_page(self, *, limit: int = 100, cursor: str | None = None):
        return self._call("fp/provenance.listPage", {"limit": limit, "cursor": cursor})
