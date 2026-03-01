"""FP client API."""

from __future__ import annotations

from typing import Any

from fp.protocol import ActivityState, EntityKind, SessionBudget


class FPClient:
    def __init__(self, server: Any) -> None:
        self._server = server

    def initialize(self, *, supported_versions: list[str], entity_id: str, profile: str | None = None) -> dict[str, Any]:
        profiles = [profile] if profile else []
        return self._server.initialize(
            supported_versions=supported_versions,
            entity_id=entity_id,
            capabilities={},
            supported_profiles=profiles,
        )

    # Entity API
    def register_entity(self, entity):
        return self._server.register_entity(entity)

    def get_entity(self, entity_id: str):
        return self._server.get_entity(entity_id)

    # Session API
    def session_create(self, *, participants: set[str], roles: dict[str, set[str]], policy_ref: str | None = None, budget: SessionBudget | None = None):
        return self._server.sessions_create(participants=participants, roles=roles, policy_ref=policy_ref, budget=budget)

    def session_get(self, session_id: str):
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
        return self._server.activities_start(
            session_id=session_id,
            owner_entity_id=owner_entity_id,
            initiator_entity_id=initiator_entity_id,
            operation=operation,
            input_payload=input_payload,
            auto_execute=auto_execute,
        )

    def activity_update(self, *, activity_id: str, state: ActivityState, status_message: str | None = None, patch: dict[str, Any] | None = None):
        return self._server.activities_update(
            activity_id=activity_id,
            state=state,
            status_message=status_message,
            patch=patch,
        )

    def activity_result(self, *, activity_id: str):
        return self._server.activities_result(activity_id=activity_id)

    def activity_cancel(self, *, activity_id: str, reason: str | None = None):
        return self._server.activities_cancel(activity_id=activity_id, reason=reason)

    # Event API
    def events_stream(self, *, session_id: str, activity_id: str | None = None, from_event_id: str | None = None):
        return self._server.events_stream(session_id=session_id, activity_id=activity_id, from_event_id=from_event_id)

    def events_read(self, *, stream_id: str, limit: int = 200):
        return self._server.events_read(stream_id=stream_id, limit=limit)

    def events_ack(self, *, stream_id: str, event_ids: list[str]):
        return self._server.events_ack(stream_id=stream_id, event_ids=event_ids)
