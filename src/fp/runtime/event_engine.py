"""Event stream engine with replay, resubscribe, and ack semantics."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from urllib.parse import urlparse
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
        normalized = self._validate_push_config(config)
        config_id = normalized["push_config_id"]
        with self._lock:
            self._push_configs[config_id] = normalized
            return dict(normalized)

    def push_config_get(self, push_config_id: str) -> dict:
        with self._lock:
            config = self._push_configs.get(push_config_id)
        if config is None:
            raise FPError(FPErrorCode.NOT_FOUND, f"push config not found: {push_config_id}")
        return dict(config)

    def push_config_list(self, *, session_id: str | None = None, activity_id: str | None = None) -> list[dict]:
        with self._lock:
            configs = list(self._push_configs.values())
        if session_id is not None:
            configs = [c for c in configs if c.get("scope", {}).get("session_id") == session_id]
        if activity_id is not None:
            configs = [c for c in configs if c.get("scope", {}).get("activity_id") == activity_id]
        return [dict(c) for c in configs]

    def push_config_delete(self, push_config_id: str) -> None:
        with self._lock:
            if push_config_id not in self._push_configs:
                raise FPError(FPErrorCode.NOT_FOUND, f"push config not found: {push_config_id}")
            del self._push_configs[push_config_id]

    def _get_state(self, stream_id: str) -> _StreamState:
        with self._lock:
            state = self._stream_states.get(stream_id)
        if state is None:
            raise FPError(FPErrorCode.NOT_FOUND, f"event stream not found: {stream_id}")
        return state

    @staticmethod
    def _validate_push_config(config: dict) -> dict:
        if not isinstance(config, dict):
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "push config must be an object")

        config_id = config.get("push_config_id")
        if not isinstance(config_id, str) or not config_id.strip():
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "push_config_id is required")

        url = config.get("url")
        if not isinstance(url, str) or not url.strip():
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "push config url must be non-empty")
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "push config url must use http/https")

        scope = config.get("scope")
        if not isinstance(scope, dict):
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "push config scope must be an object")
        session_id = scope.get("session_id")
        activity_id = scope.get("activity_id")
        if session_id is not None and (not isinstance(session_id, str) or not session_id.strip()):
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "push config scope.session_id must be non-empty string")
        if activity_id is not None and (not isinstance(activity_id, str) or not activity_id.strip()):
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "push config scope.activity_id must be non-empty string")
        if session_id is None and activity_id is None:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "push config scope requires session_id or activity_id")

        auth = config.get("auth", {})
        if not isinstance(auth, dict):
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "push config auth must be an object")

        event_types = config.get("event_types")
        if not isinstance(event_types, list) or not event_types:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "push config event_types must be a non-empty array")
        normalized_event_types: list[str] = []
        for event_type in event_types:
            if not isinstance(event_type, str) or not event_type.strip():
                raise FPError(FPErrorCode.INVALID_ARGUMENT, "push config event_types must contain non-empty strings")
            normalized_event_types.append(event_type)

        normalized_scope: dict[str, str] = {}
        if isinstance(session_id, str) and session_id.strip():
            normalized_scope["session_id"] = session_id
        if isinstance(activity_id, str) and activity_id.strip():
            normalized_scope["activity_id"] = activity_id

        return {
            "push_config_id": config_id,
            "url": url,
            "scope": normalized_scope,
            "auth": dict(auth),
            "event_types": normalized_event_types,
        }
