"""In-process transport for lowest-latency integration and tests."""

from __future__ import annotations

from typing import Any


class InProcessTransport:
    def __init__(self, server: Any) -> None:
        self._server = server

    @property
    def server(self) -> Any:
        return self._server
