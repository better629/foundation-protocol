"""Event stream engine with replay, resubscribe, and ack semantics."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from uuid import uuid4

from fp.protocol import EventStreamHandle, FPError, FPErrorCode, FPEvent
from fp.runtime.backpressure import BackpressureController
from fp.stores.interfaces import EventStore


@dataclass(slots=True)
class _StreamState:
    stream_id: str
    session_id: str
    activity_id: str | None
    cursor_event_id: str | None = None
    acked_event_ids: set[str] = field(default_factory=set)


class EventEngine:
    def __init__(self, store: EventStore, *, backpressure_window: int = 500) -> None:
        self._store = store
        self._lock = RLock()
        self._stream_states: dict[str, _StreamState] = {}
        self._backpressure = BackpressureController(default_window=backpressure_window)
        self._push_configs: dict[str, dict] = {}

    @staticmethod
    def _stream_key(session_id: str, activity_id: str | None) -> str:
        return f"{session_id}:{activity_id or '*'}"

    def publish(self, event: FPEvent) -> FPEvent:
        session_key = self._stream_key(event.session_id, None)
        self._store.append(session_key, [event])
        if event.activity_id:
            activity_key = self._stream_key(event.session_id, event.activity_id)
            self._store.append(activity_key, [event])
        return event

    def stream(
        self,
        *,
        session_id: str,
        activity_id: str | None = None,
        from_event_id: str | None = None,
    ) -> EventStreamHandle:
        stream_id = f"stream-{uuid4().hex}"
        state = _StreamState(
            stream_id=stream_id,
            session_id=session_id,
            activity_id=activity_id,
            cursor_event_id=from_event_id,
        )
        with self._lock:
            self._stream_states[stream_id] = state
        self._backpressure.configure_stream(stream_id)
        return EventStreamHandle(
            stream_id=stream_id,
            session_id=session_id,
            activity_id=activity_id,
            last_read_event_id=from_event_id,
        )

    def read(self, stream_id: str, *, limit: int = 200) -> list[FPEvent]:
        if limit <= 0:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "events.read limit must be > 0")
        state = self._get_state(stream_id)
        stream_key = self._stream_key(state.session_id, state.activity_id)
        events = self._store.replay_from(stream_key, state.cursor_event_id, limit=limit)
        if events:
            self._backpressure.on_deliver(stream_id, len(events))
            state.cursor_event_id = events[-1].event_id
        return events

    def resubscribe(self, stream_id: str, *, last_event_id: str) -> EventStreamHandle:
        state = self._get_state(stream_id)
        state.cursor_event_id = last_event_id
        return EventStreamHandle(
            stream_id=stream_id,
            session_id=state.session_id,
            activity_id=state.activity_id,
            last_read_event_id=state.cursor_event_id,
        )

    def ack(self, stream_id: str, event_ids: list[str]) -> None:
        state = self._get_state(stream_id)
        state.acked_event_ids.update(event_ids)
        self._backpressure.on_ack(stream_id, len(event_ids))

    def push_config_set(self, config: dict) -> dict:
        config_id = config.get("push_config_id")
        if not config_id:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "push_config_id is required")
        self._push_configs[config_id] = dict(config)
        return dict(config)

    def push_config_get(self, push_config_id: str) -> dict:
        config = self._push_configs.get(push_config_id)
        if config is None:
            raise FPError(FPErrorCode.NOT_FOUND, f"push config not found: {push_config_id}")
        return dict(config)

    def push_config_list(self, *, session_id: str | None = None, activity_id: str | None = None) -> list[dict]:
        configs = list(self._push_configs.values())
        if session_id is not None:
            configs = [c for c in configs if c.get("scope", {}).get("session_id") == session_id]
        if activity_id is not None:
            configs = [c for c in configs if c.get("scope", {}).get("activity_id") == activity_id]
        return [dict(c) for c in configs]

    def push_config_delete(self, push_config_id: str) -> None:
        if push_config_id not in self._push_configs:
            raise FPError(FPErrorCode.NOT_FOUND, f"push config not found: {push_config_id}")
        del self._push_configs[push_config_id]

    def _get_state(self, stream_id: str) -> _StreamState:
        with self._lock:
            state = self._stream_states.get(stream_id)
        if state is None:
            raise FPError(FPErrorCode.NOT_FOUND, f"event stream not found: {stream_id}")
        return state
