from __future__ import annotations

import unittest

from fp.economy import MeteringService, ReceiptService


class ReceiptThirdPartyVerifyTests(unittest.TestCase):
    def test_third_party_can_verify_without_shared_secret(self) -> None:
        meter = MeteringService().record(
            subject_ref="act-2",
            unit="gpu-hour",
            quantity=2,
            metering_policy_ref="policy:meter",
        )
        issuer = ReceiptService(signing_mode="ed25519", key_ref="did:example:issuer#receipt")
        receipt = issuer.issue(
            activity_id="act-2",
            provider_entity_id="fp:agent:issuer",
            meter_records=[meter],
        )

        verifier = ReceiptService(
            signing_mode="ed25519",
            public_keys={issuer.key_ref: issuer.public_key_pem},
        )
        self.assertTrue(verifier.verify(receipt))


if __name__ == "__main__":
    unittest.main()
