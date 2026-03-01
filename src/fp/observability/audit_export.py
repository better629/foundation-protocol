"""Audit package exporter."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from fp.protocol import FPEvent, ProvenanceRecord, Receipt, Settlement


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value


def export_audit_bundle(
    *,
    session_id: str,
    events: list[FPEvent],
    provenance: list[ProvenanceRecord],
    receipts: list[Receipt],
    settlements: list[Settlement],
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "exported_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "events": [_to_jsonable(asdict(event)) for event in events],
        "provenance": [_to_jsonable(asdict(record)) for record in provenance],
        "receipts": [_to_jsonable(asdict(receipt)) for receipt in receipts],
        "settlements": [_to_jsonable(asdict(settlement)) for settlement in settlements],
    }
