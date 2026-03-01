"""SSE formatting helpers."""

from __future__ import annotations

import json
from typing import Any


def format_sse(event: str, data: dict[str, Any], event_id: str | None = None) -> str:
    chunks: list[str] = []
    if event_id is not None:
        chunks.append(f"id: {event_id}")
    chunks.append(f"event: {event}")
    chunks.append(f"data: {json.dumps(data, separators=(',', ':'))}")
    return "\n".join(chunks) + "\n\n"
