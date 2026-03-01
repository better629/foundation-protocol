"""Settlement primitives."""

from __future__ import annotations

from uuid import uuid4

from fp.protocol import Settlement, SettlementStatus


class SettlementService:
    def create(
        self,
        *,
        receipt_refs: list[str],
        settlement_ref: str,
        amount: float | None = None,
        currency: str | None = None,
    ) -> Settlement:
        return Settlement(
            settlement_id=f"stl-{uuid4().hex}",
            receipt_refs=receipt_refs,
            settlement_ref=settlement_ref,
            amount=amount,
            currency=currency,
        )

    def confirm(self, settlement: Settlement) -> Settlement:
        settlement.status = SettlementStatus.CONFIRMED
        return settlement

    def reject(self, settlement: Settlement) -> Settlement:
        settlement.status = SettlementStatus.REJECTED
        return settlement
