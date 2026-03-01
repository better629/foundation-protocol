"""Stdio transport helpers."""

from __future__ import annotations

import json
from typing import Any


def encode_message(payload: dict[str, Any]) -> str:
    return json.dumps(payload, separators=(",", ":")) + "\n"


def decode_message(line: str) -> dict[str, Any]:
    return json.loads(line)
