"""Trace utilities."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4


def new_trace_id() -> str:
    return f"trace-{uuid4().hex}"


def new_span_id() -> str:
    return f"span-{uuid4().hex}"


@dataclass(slots=True)
class TraceContext:
    trace_id: str
    span_id: str
    parent_span_id: str | None = None
