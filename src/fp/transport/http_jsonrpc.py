"""HTTP/JSON-RPC transport placeholders for app-layer integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class JSONRPCRequest:
    method: str
    params: dict[str, Any]
    id: str | int | None = None


@dataclass(slots=True)
class JSONRPCResponse:
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    id: str | int | None = None
