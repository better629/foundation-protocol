"""Receipt issuance and validation."""

from __future__ import annotations

import json
from dataclasses import asdict
from uuid import uuid4

from fp.protocol import MeterRecord, Receipt
from fp.security.ed25519 import (
    ed25519_available,
    generate_ed25519_keypair_pem,
    sign_ed25519,
    verify_ed25519,
)
from fp.security.signatures import sign_hmac_sha256, verify_hmac_sha256


class ReceiptService:
    def __init__(
        self,
        secret: str = "fp-local-secret",
        *,
        signing_mode: str = "auto",
        private_key_pem: str | None = None,
        public_key_pem: str | None = None,
        key_ref: str = "fp:local#receipt-signing-key",
        public_keys: dict[str, str] | None = None,
    ) -> None:
        self._secret = secret
        self._key_ref = key_ref
        self._public_keys = dict(public_keys or {})
        mode = signing_mode
        if mode == "auto":
            mode = "ed25519" if ed25519_available() else "hmac"
        if mode not in {"ed25519", "hmac"}:
            raise ValueError("signing_mode must be one of: auto, ed25519, hmac")
        self._signing_mode = mode
        self._private_key_pem = private_key_pem
        self._public_key_pem = public_key_pem
        if self._signing_mode == "ed25519":
            if self._private_key_pem is None and self._public_key_pem is None:
                self._private_key_pem, self._public_key_pem = generate_ed25519_keypair_pem()
            elif self._private_key_pem is not None and self._public_key_pem is None:
                raise ValueError("public_key_pem is required when private_key_pem is provided")
            if self._public_key_pem is not None:
                self._public_keys.setdefault(self._key_ref, self._public_key_pem)

    def issue(self, *, activity_id: str, provider_entity_id: str, meter_records: list[MeterRecord]) -> Receipt:
        receipt_id = f"rcpt-{uuid4().hex}"
        payload = self._canonical_payload(
            receipt_id=receipt_id,
            activity_id=activity_id,
            provider_entity_id=provider_entity_id,
            meter_records=meter_records,
        )
        integrity_proof: str
        if self._signing_mode == "ed25519":
            if self._private_key_pem is None:
                raise ValueError("private_key_pem is required to issue ed25519 receipts")
            signature = sign_ed25519(payload, self._private_key_pem)
            integrity_proof = f"ed25519:{self._key_ref}:{signature}"
        else:
            signature = sign_hmac_sha256(payload, self._secret)
            integrity_proof = f"hmac-sha256:{signature}"
        return Receipt(
            receipt_id=receipt_id,
            activity_id=activity_id,
            provider_entity_id=provider_entity_id,
            meter_records=meter_records,
            integrity_proof=integrity_proof,
        )

    def verify(self, receipt: Receipt) -> bool:
        payload = self._canonical_payload(
            receipt_id=receipt.receipt_id,
            activity_id=receipt.activity_id,
            provider_entity_id=receipt.provider_entity_id,
            meter_records=receipt.meter_records,
        )
        if receipt.integrity_proof.startswith("ed25519:"):
            encoded = receipt.integrity_proof[len("ed25519:") :]
            if ":" not in encoded:
                return False
            key_ref, signature = encoded.rsplit(":", 1)
            if not key_ref or not signature:
                return False
            public_key = self._public_keys.get(key_ref)
            if public_key is None and self._public_key_pem is not None:
                public_key = self._public_key_pem
            if public_key is None:
                return False
            return verify_ed25519(payload, signature, public_key)
        if receipt.integrity_proof.startswith("hmac-sha256:"):
            signature = receipt.integrity_proof.split(":", 1)[-1]
            if not signature:
                return False
            return verify_hmac_sha256(payload, self._secret, signature)
        return False

    @property
    def key_ref(self) -> str:
        return self._key_ref

    @property
    def public_key_pem(self) -> str | None:
        return self._public_key_pem

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
