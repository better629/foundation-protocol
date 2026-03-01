"""Websocket transport placeholder."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class WebsocketMessage:
    type: str
    payload: dict[str, Any]
