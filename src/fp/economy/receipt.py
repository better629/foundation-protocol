"""Receipt issuance and validation."""

from __future__ import annotations

import json
from dataclasses import asdict
from uuid import uuid4

from fp.protocol import MeterRecord, Receipt
from fp.security import sign_hmac_sha256, verify_hmac_sha256


class ReceiptService:
    def __init__(self, secret: str = "fp-local-secret") -> None:
        self._secret = secret

    def issue(self, *, activity_id: str, provider_entity_id: str, meter_records: list[MeterRecord]) -> Receipt:
        receipt_id = f"rcpt-{uuid4().hex}"
        payload = self._canonical_payload(
            receipt_id=receipt_id,
            activity_id=activity_id,
            provider_entity_id=provider_entity_id,
            meter_records=meter_records,
        )
        signature = sign_hmac_sha256(payload, self._secret)
        return Receipt(
            receipt_id=receipt_id,
            activity_id=activity_id,
            provider_entity_id=provider_entity_id,
            meter_records=meter_records,
            integrity_proof=f"hmac-sha256:{signature}",
        )

    def verify(self, receipt: Receipt) -> bool:
        if not receipt.integrity_proof.startswith("hmac-sha256:"):
            return False
        signature = receipt.integrity_proof.split(":", 1)[-1]
        if not signature:
            return False
        payload = self._canonical_payload(
            receipt_id=receipt.receipt_id,
            activity_id=receipt.activity_id,
            provider_entity_id=receipt.provider_entity_id,
            meter_records=receipt.meter_records,
        )
        return verify_hmac_sha256(payload, self._secret, signature)

    @staticmethod
    def _canonical_payload(
        *,
        receipt_id: str,
        activity_id: str,
        provider_entity_id: str,
        meter_records: list[MeterRecord],
    ) -> bytes:
        body = {
            "receipt_id": receipt_id,
            "activity_id": activity_id,
            "provider_entity_id": provider_entity_id,
            "meter_records": [asdict(record) for record in meter_records],
        }
        return json.dumps(body, default=str, sort_keys=True, separators=(",", ":")).encode("utf-8")
