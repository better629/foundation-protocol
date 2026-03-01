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
        payload = json.dumps(
            [asdict(record) for record in meter_records],
            default=str,
            separators=(",", ":"),
        ).encode("utf-8")
        signature = sign_hmac_sha256(payload, self._secret)
        return Receipt(
            receipt_id=f"rcpt-{uuid4().hex}",
            activity_id=activity_id,
            provider_entity_id=provider_entity_id,
            meter_records=meter_records,
            integrity_proof=f"hmac-sha256:{signature}",
        )

    def verify(self, receipt: Receipt) -> bool:
        payload = json.dumps(
            [asdict(record) for record in receipt.meter_records],
            default=str,
            separators=(",", ":"),
        ).encode("utf-8")
        signature = receipt.integrity_proof.split(":", 1)[-1]
        return verify_hmac_sha256(payload, self._secret, signature)
