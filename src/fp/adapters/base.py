"""Framework adapter contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from fp.protocol import ActivityState


@dataclass(slots=True)
class AdapterEvent:
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AdapterStartResult:
    state: ActivityState
    output: dict[str, Any] = field(default_factory=dict)
    output_ref: str | None = None
    events: list[AdapterEvent] = field(default_factory=list)


@dataclass(slots=True)
class AdapterCancelResult:
    canceled: bool
    reason: str | None = None


@dataclass(slots=True)
class AdapterResult:
    output: dict[str, Any] = field(default_factory=dict)
    output_ref: str | None = None


class FrameworkAdapter(Protocol):
    async def start_activity(self, ctx: dict[str, Any], req: dict[str, Any]) -> AdapterStartResult: ...

    async def cancel_activity(self, ctx: dict[str, Any], activity_id: str) -> AdapterCancelResult: ...

    async def poll_updates(self, ctx: dict[str, Any], activity_id: str) -> list[AdapterEvent]: ...

    async def fetch_result(self, ctx: dict[str, Any], activity_id: str) -> AdapterResult: ...
