"""Metering primitives."""

from __future__ import annotations

from uuid import uuid4

from fp.protocol import MeterRecord


class MeteringService:
    def record(
        self,
        *,
        subject_ref: str,
        unit: str,
        quantity: float,
        metering_policy_ref: str,
        metadata: dict[str, str] | None = None,
    ) -> MeterRecord:
        return MeterRecord(
            meter_id=f"meter-{uuid4().hex}",
            subject_ref=subject_ref,
            unit=unit,
            quantity=quantity,
            metering_policy_ref=metering_policy_ref,
            metadata=metadata or {},
        )
