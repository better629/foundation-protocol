"""Normalization helpers that keep FP semantics canonical."""

from __future__ import annotations

from .errors import FPError, FPErrorCode
from .models import ActivityState


_STATE_ALIASES = {
    "cancelled": ActivityState.CANCELED,
    "canceled": ActivityState.CANCELED,
    "submitted": ActivityState.SUBMITTED,
    "working": ActivityState.WORKING,
    "input-required": ActivityState.INPUT_REQUIRED,
    "input_required": ActivityState.INPUT_REQUIRED,
    "auth-required": ActivityState.AUTH_REQUIRED,
    "auth_required": ActivityState.AUTH_REQUIRED,
    "completed": ActivityState.COMPLETED,
    "failed": ActivityState.FAILED,
    "rejected": ActivityState.REJECTED,
}


def normalize_activity_state(value: str | ActivityState) -> ActivityState:
    if isinstance(value, ActivityState):
        return value
    lowered = value.strip().lower()
    if lowered in _STATE_ALIASES:
        return _STATE_ALIASES[lowered]
    raise FPError(
        FPErrorCode.INVALID_ARGUMENT,
        message=f"unknown activity state: {value}",
    )


def normalize_event_type(event_type: str) -> str:
    return event_type.strip().lower().replace(" ", "-")
