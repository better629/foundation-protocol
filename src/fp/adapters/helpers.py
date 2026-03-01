"""Adapter helper utilities."""

from __future__ import annotations

from fp.protocol import ActivityState
from fp.protocol.normalize import normalize_activity_state


class AdapterHelper:
    @staticmethod
    def normalize_state(value: str | ActivityState) -> ActivityState:
        return normalize_activity_state(value)
