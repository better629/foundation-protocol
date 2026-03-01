"""Activity lifecycle engine."""

from __future__ import annotations

from fp.protocol import Activity, ActivityState, FPError, FPErrorCode, utc_now
from fp.protocol.normalize import normalize_activity_state
from fp.stores.interfaces import ActivityStore

_ALLOWED_TRANSITIONS: dict[ActivityState, set[ActivityState]] = {
    ActivityState.SUBMITTED: {ActivityState.WORKING, ActivityState.CANCELED, ActivityState.REJECTED},
    ActivityState.WORKING: {
        ActivityState.INPUT_REQUIRED,
        ActivityState.AUTH_REQUIRED,
        ActivityState.COMPLETED,
        ActivityState.FAILED,
        ActivityState.CANCELED,
        ActivityState.REJECTED,
    },
    ActivityState.INPUT_REQUIRED: {ActivityState.WORKING, ActivityState.CANCELED},
    ActivityState.AUTH_REQUIRED: {ActivityState.WORKING, ActivityState.CANCELED, ActivityState.REJECTED},
    ActivityState.COMPLETED: set(),
    ActivityState.FAILED: set(),
    ActivityState.CANCELED: set(),
    ActivityState.REJECTED: set(),
}


class ActivityEngine:
    def __init__(self, store: ActivityStore) -> None:
        self._store = store

    def start(
        self,
        *,
        activity_id: str,
        session_id: str,
        owner_entity_id: str,
        initiator_entity_id: str,
        operation: str,
        input_payload: dict,
    ) -> Activity:
        if self._store.get(activity_id) is not None:
            raise FPError(FPErrorCode.ALREADY_EXISTS, f"activity already exists: {activity_id}")
        activity = Activity(
            activity_id=activity_id,
            session_id=session_id,
            owner_entity_id=owner_entity_id,
            initiator_entity_id=initiator_entity_id,
            operation=operation,
            input_payload=input_payload,
            state=ActivityState.SUBMITTED,
        )
        self._store.put(activity)
        return activity

    def get(self, activity_id: str) -> Activity:
        activity = self._store.get(activity_id)
        if activity is None:
            raise FPError(FPErrorCode.NOT_FOUND, f"activity not found: {activity_id}")
        return activity

    def transition(
        self,
        activity_id: str,
        *,
        next_state: ActivityState | str,
        status_message: str | None = None,
        patch: dict | None = None,
    ) -> Activity:
        activity = self.get(activity_id)
        normalized = normalize_activity_state(next_state)
        allowed = _ALLOWED_TRANSITIONS[activity.state]
        if normalized not in allowed:
            raise FPError(
                FPErrorCode.INVALID_STATE_TRANSITION,
                message=f"{activity.state.value} -> {normalized.value} is not allowed",
            )
        activity.state = normalized
        activity.status_message = status_message
        if patch:
            activity.input_payload.update(patch)
        activity.updated_at = utc_now()
        self._store.put(activity)
        return activity

    def complete(self, activity_id: str, *, result_payload: dict | None = None, result_ref: str | None = None) -> Activity:
        activity = self.get(activity_id)
        if activity.state not in {
            ActivityState.SUBMITTED,
            ActivityState.WORKING,
            ActivityState.INPUT_REQUIRED,
            ActivityState.AUTH_REQUIRED,
        }:
            raise FPError(FPErrorCode.INVALID_STATE_TRANSITION, "activity cannot be completed from current state")
        activity.state = ActivityState.COMPLETED
        activity.result_payload = result_payload
        activity.result_ref = result_ref
        activity.updated_at = utc_now()
        self._store.put(activity)
        return activity

    def fail(self, activity_id: str, *, message: str, details: dict | None = None) -> Activity:
        activity = self.get(activity_id)
        activity.state = ActivityState.FAILED
        activity.error = {"message": message, "details": details or {}}
        activity.updated_at = utc_now()
        self._store.put(activity)
        return activity

    def cancel(self, activity_id: str, *, reason: str | None = None) -> Activity:
        activity = self.get(activity_id)
        if activity.state in {ActivityState.COMPLETED, ActivityState.FAILED, ActivityState.CANCELED, ActivityState.REJECTED}:
            raise FPError(FPErrorCode.INVALID_STATE_TRANSITION, "activity already terminated")
        activity.state = ActivityState.CANCELED
        activity.status_message = reason
        activity.updated_at = utc_now()
        self._store.put(activity)
        return activity

    def list(self, *, session_id: str | None = None, state: ActivityState | None = None, owner_entity_id: str | None = None) -> list[Activity]:
        activities = self._store.list(session_id=session_id)
        if state is not None:
            activities = [activity for activity in activities if activity.state is state]
        if owner_entity_id is not None:
            activities = [activity for activity in activities if activity.owner_entity_id == owner_entity_id]
        return activities
