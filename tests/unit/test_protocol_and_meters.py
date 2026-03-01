from __future__ import annotations

import unittest

from fp.economy import ReceiptService
from fp.observability import CostMeter, CostModel, TokenMeter
from fp.observability.audit_export import export_audit_bundle
from fp.protocol import MeterRecord
from fp.protocol.normalize import normalize_activity_state
from fp.security import sign_hmac_sha256, verify_hmac_sha256


class ProtocolAndMeterTests(unittest.TestCase):
    def test_activity_state_normalization(self) -> None:
        self.assertEqual(normalize_activity_state("cancelled").value, "canceled")
        self.assertEqual(normalize_activity_state("input-required").value, "input_required")

    def test_token_and_cost_meter(self) -> None:
        meter = TokenMeter()
        usage = meter.measure(input_payload={"prompt": "hello world"}, output_payload={"text": "ok"})
        self.assertGreater(usage.input_tokens, 0)
        self.assertGreater(usage.output_tokens, 0)

        cost = CostMeter(CostModel(input_per_1k_tokens=0.001, output_per_1k_tokens=0.002)).estimate(usage)
        self.assertGreater(cost, 0)

    def test_signature_roundtrip(self) -> None:
        payload = b"fp-proof"
        secret = "secret"
        signature = sign_hmac_sha256(payload, secret)
        self.assertTrue(verify_hmac_sha256(payload, secret, signature))

    def test_audit_bundle_is_jsonable(self) -> None:
        bundle = export_audit_bundle(
            session_id="sess-1",
            events=[],
            provenance=[],
            receipts=[],
            settlements=[],
        )
        self.assertTrue(bundle["exported_at"].endswith("Z"))

    def test_receipt_verification_detects_context_tampering(self) -> None:
        service = ReceiptService(secret="test-secret")
        record = MeterRecord(
            meter_id="mtr-1",
            subject_ref="act-1",
            unit="token",
            quantity=100,
            metering_policy_ref="policy:meter",
        )
        receipt = service.issue(
            activity_id="act-1",
            provider_entity_id="fp:agent:provider",
            meter_records=[record],
        )

        self.assertTrue(service.verify(receipt))

        receipt.activity_id = "act-2"
        self.assertFalse(service.verify(receipt))


if __name__ == "__main__":
    unittest.main()
