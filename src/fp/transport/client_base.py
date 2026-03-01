"""Client transport protocol for FP clients."""

from __future__ import annotations

from typing import Any, Protocol


class ClientTransport(Protocol):
    def call(self, method: str, params: dict[str, Any] | None = None) -> Any: ...
