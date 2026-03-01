"""Adapter registry."""

from __future__ import annotations

from fp.protocol import FPError, FPErrorCode


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, object] = {}

    def register(self, name: str, adapter: object) -> None:
        self._adapters[name] = adapter

    def get(self, name: str) -> object:
        adapter = self._adapters.get(name)
        if adapter is None:
            raise FPError(FPErrorCode.NOT_FOUND, f"adapter not found: {name}")
        return adapter

    def list(self) -> list[str]:
        return sorted(self._adapters.keys())
