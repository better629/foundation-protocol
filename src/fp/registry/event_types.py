"""Event type registry."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class EventType:
    name: str
    description: str
    required_fields: list[str] = field(default_factory=list)


class EventTypeRegistry:
    def __init__(self) -> None:
        self._types: dict[str, EventType] = {}

    def register(self, event_type: EventType) -> EventType:
        self._types[event_type.name] = event_type
        return event_type

    def get(self, name: str) -> EventType | None:
        return self._types.get(name)

    def list(self) -> list[EventType]:
        return list(self._types.values())
