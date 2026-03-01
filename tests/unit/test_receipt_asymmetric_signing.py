from __future__ import annotations

import unittest

from fp.economy import MeteringService, ReceiptService


class ReceiptAsymmetricSigningTests(unittest.TestCase):
    def test_receipt_service_issues_and_verifies_ed25519_receipt(self) -> None:
        meter = MeteringService().record(
            subject_ref="act-1",
            unit="token",
            quantity=123,
            metering_policy_ref="policy:meter",
        )
        service = ReceiptService(signing_mode="ed25519", key_ref="did:example:provider#receipt")
        receipt = service.issue(
            activity_id="act-1",
            provider_entity_id="fp:agent:provider",
            meter_records=[meter],
        )

        self.assertTrue(receipt.integrity_proof.startswith("ed25519:"))
        self.assertTrue(service.verify(receipt))


if __name__ == "__main__":
    unittest.main()
