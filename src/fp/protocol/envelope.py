"""Envelope helpers for FP message families."""

from __future__ import annotations

from dataclasses import replace
from typing import Any
from uuid import uuid4

from .models import Envelope, MessageFamily


def new_envelope(
    *,
    fp_version: str,
    family: MessageFamily,
    trace_id: str,
    from_entity: str,
    to_entity: str,
    payload: dict[str, Any],
    session_id: str | None = None,
    activity_id: str | None = None,
    policy_ref: str | None = None,
) -> Envelope:
    """Create a fresh envelope with generated message/span ids."""

    return Envelope(
        fp_version=fp_version,
        message_id=f"msg-{uuid4().hex}",
        family=family,
        trace_id=trace_id,
        span_id=f"span-{uuid4().hex}",
        from_entity=from_entity,
        to_entity=to_entity,
        session_id=session_id,
        activity_id=activity_id,
        policy_ref=policy_ref,
        payload=payload,
    )


def derive_child_envelope(parent: Envelope, *, family: MessageFamily, payload: dict[str, Any]) -> Envelope:
    """Create a child envelope preserving trace lineage."""

    return replace(
        parent,
        message_id=f"msg-{uuid4().hex}",
        span_id=f"span-{uuid4().hex}",
        causation_id=parent.message_id,
        family=family,
        payload=payload,
    )
