"""Activity-domain runtime module."""

from __future__ import annotations

from typing import Any, Callable

from fp.protocol import Activity, ActivityState
from fp.runtime.activity_engine import ActivityEngine
from fp.runtime.dispatch_engine import DispatchContext, DispatchEngine


class ActivityModule:
    def __init__(self, *, engine: ActivityEngine, dispatch: DispatchEngine) -> None:
        self.engine = engine
        self.dispatch = dispatch

    def register_operation(self, name: str, handler: Callable[[dict[str, Any]], Any]) -> None:
        self.dispatch.register(name, handler)

    def has_operation(self, name: str) -> bool:
        return self.dispatch.has_handler(name)

    def execute(self, *, context: DispatchContext, input_payload: dict[str, Any]) -> Any:
        return self.dispatch.execute(context=context, input_payload=input_payload)

    def start(
        self,
        *,
        activity_id: str,
        session_id: str,
        owner_entity_id: str,
        initiator_entity_id: str,
        operation: str,
        input_payload: dict[str, Any],
    ) -> Activity:
        return self.engine.start(
            activity_id=activity_id,
            session_id=session_id,
            owner_entity_id=owner_entity_id,
            initiator_entity_id=initiator_entity_id,
            operation=operation,
            input_payload=input_payload,
        )

    def transition(
        self,
        activity_id: str,
        *,
        next_state: ActivityState | str,
        status_message: str | None = None,
        patch: dict[str, Any] | None = None,
    ) -> Activity:
        return self.engine.transition(activity_id, next_state=next_state, status_message=status_message, patch=patch)

    def complete(self, activity_id: str, *, result_payload: dict[str, Any] | None = None, result_ref: str | None = None) -> Activity:
        return self.engine.complete(activity_id, result_payload=result_payload, result_ref=result_ref)

    def fail(self, activity_id: str, *, message: str, details: dict[str, Any] | None = None) -> Activity:
        return self.engine.fail(activity_id, message=message, details=details)

    def cancel(self, activity_id: str, *, reason: str | None = None) -> Activity:
        return self.engine.cancel(activity_id, reason=reason)

    def get(self, activity_id: str) -> Activity:
        return self.engine.get(activity_id)

    def list(
        self,
        *,
        session_id: str | None = None,
        state: ActivityState | None = None,
        owner_entity_id: str | None = None,
    ) -> list[Activity]:
        return self.engine.list(session_id=session_id, state=state, owner_entity_id=owner_entity_id)
