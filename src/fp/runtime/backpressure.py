"""Backpressure controller for event stream safety."""

from __future__ import annotations

from collections import defaultdict
from threading import RLock

from fp.protocol.errors import FPError, FPErrorCode


class BackpressureController:
    def __init__(self, default_window: int = 500) -> None:
        self._window = default_window
        self._lock = RLock()
        self._outstanding: dict[str, int] = defaultdict(int)

    def configure_stream(self, stream_id: str, *, window: int | None = None) -> None:
        with self._lock:
            if window is not None:
                self._window = window
            self._outstanding.setdefault(stream_id, 0)

    def on_deliver(self, stream_id: str, delivered_count: int) -> None:
        with self._lock:
            outstanding = self._outstanding[stream_id] + delivered_count
            if outstanding > self._window:
                raise FPError(
                    FPErrorCode.BACKPRESSURE,
                    message="event stream is over backpressure window",
                    details={"stream_id": stream_id, "window": self._window, "outstanding": outstanding},
                    retryable=True,
                )
            self._outstanding[stream_id] = outstanding

    def on_ack(self, stream_id: str, ack_count: int) -> None:
        with self._lock:
            current = self._outstanding.get(stream_id, 0)
            self._outstanding[stream_id] = max(0, current - ack_count)

    def outstanding(self, stream_id: str) -> int:
        with self._lock:
            return self._outstanding.get(stream_id, 0)
