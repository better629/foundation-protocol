"""Economy-domain runtime module."""

from __future__ import annotations

from typing import Any

from fp.economy import DisputeService, MeteringService, ReceiptService, SettlementService
from fp.protocol import Dispute, Settlement


class EconomyModule:
    def __init__(
        self,
        *,
        metering: MeteringService,
        receipts: ReceiptService,
        settlements: SettlementService,
        disputes: DisputeService,
    ) -> None:
        self.metering = metering
        self.receipts = receipts
        self.settlements = settlements
        self.disputes = disputes

    def meter_record(
        self,
        *,
        subject_ref: str,
        unit: str,
        quantity: float,
        metering_policy_ref: str,
        metadata: dict[str, str] | None = None,
    ) -> Any:
        return self.metering.record(
            subject_ref=subject_ref,
            unit=unit,
            quantity=quantity,
            metering_policy_ref=metering_policy_ref,
            metadata=metadata,
        )

    def issue_receipt(self, *, activity_id: str, provider_entity_id: str, meter_records: list) -> Any:
        return self.receipts.issue(
            activity_id=activity_id,
            provider_entity_id=provider_entity_id,
            meter_records=meter_records,
        )

    def create_settlement(
        self,
        *,
        receipt_refs: list[str],
        settlement_ref: str,
        amount: float | None = None,
        currency: str | None = None,
    ) -> Settlement:
        return self.settlements.create(
            receipt_refs=receipt_refs,
            settlement_ref=settlement_ref,
            amount=amount,
            currency=currency,
        )

    def confirm_settlement(self, settlement: Settlement) -> Settlement:
        return self.settlements.confirm(settlement)

    def open_dispute(
        self,
        *,
        target_ref: str,
        reason_code: str,
        claimant_entity_id: str,
        evidence_refs: list[str] | None = None,
    ) -> Dispute:
        return self.disputes.open(
            target_ref=target_ref,
            reason_code=reason_code,
            claimant_entity_id=claimant_entity_id,
            evidence_refs=evidence_refs,
        )
