"""Event-domain runtime module."""

from __future__ import annotations

from fp.protocol import FPEvent
from fp.runtime.event_engine import EventEngine


class EventModule:
    def __init__(self, engine: EventEngine) -> None:
        self.engine = engine

    def publish(self, event: FPEvent) -> FPEvent:
        return self.engine.publish(event)

    def stream(self, *, session_id: str, activity_id: str | None = None, from_event_id: str | None = None):
        return self.engine.stream(session_id=session_id, activity_id=activity_id, from_event_id=from_event_id)

    def read(self, stream_id: str, *, limit: int = 200) -> list[FPEvent]:
        return self.engine.read(stream_id, limit=limit)

    def resubscribe(self, stream_id: str, *, last_event_id: str):
        return self.engine.resubscribe(stream_id, last_event_id=last_event_id)

    def ack(self, stream_id: str, event_ids: list[str]) -> None:
        self.engine.ack(stream_id, event_ids)

    def push_config_set(self, config: dict) -> dict:
        return self.engine.push_config_set(config)

    def push_config_get(self, push_config_id: str) -> dict:
        return self.engine.push_config_get(push_config_id)

    def push_config_list(self, *, session_id: str | None = None, activity_id: str | None = None) -> list[dict]:
        return self.engine.push_config_list(session_id=session_id, activity_id=activity_id)

    def push_config_delete(self, push_config_id: str) -> None:
        self.engine.push_config_delete(push_config_id)
