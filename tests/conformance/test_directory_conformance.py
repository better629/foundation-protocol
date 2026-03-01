from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from fp.federation import DirectoryService, FPServerCard, sign_server_card
from fp.protocol import FPError, FPErrorCode
from fp.security.ed25519 import ed25519_available, generate_ed25519_keypair_pem


@unittest.skipUnless(ed25519_available(), "cryptography is required for directory signing tests")
class DirectoryConformanceTests(unittest.TestCase):
    def test_directory_accepts_valid_signed_card(self) -> None:
        private_key, public_key = generate_ed25519_keypair_pem()
        key_ref = "did:example:node-1#fp-card"
        directory = DirectoryService(public_keys={key_ref: public_key}, require_signature=True)

        card = sign_server_card(
            FPServerCard(
                card_id="card-1",
                entity_id="fp:agent:node-1",
                fp_version="0.1.0",
                rpc_url="https://node-1.example/rpc",
                well_known_url="https://node-1.example/.well-known/fp-server.json",
                ttl_seconds=600,
            ),
            private_key_pem=private_key,
            key_ref=key_ref,
        )

        directory.publish(card, actor_ref="publisher")
        resolved = directory.resolve("fp:agent:node-1")
        self.assertEqual(resolved.entity_id, "fp:agent:node-1")
        self.assertEqual(resolved.sign_alg, "ed25519")

    def test_directory_rejects_unsigned_card_when_signature_required(self) -> None:
        directory = DirectoryService(require_signature=True)
        unsigned = FPServerCard(
            card_id="card-unsigned",
            entity_id="fp:agent:unsigned",
            fp_version="0.1.0",
            rpc_url="https://unsigned.example/rpc",
            well_known_url="https://unsigned.example/.well-known/fp-server.json",
            sign_alg="none",
            key_ref="fp:agent:unsigned#local",
            signature="unsigned",
            ttl_seconds=600,
        )
        with self.assertRaises(FPError) as exc:
            directory.publish(unsigned, actor_ref="publisher")
        self.assertIs(exc.exception.code, FPErrorCode.AUTH_REQUIRED)

    def test_directory_rejects_expired_card(self) -> None:
        private_key, public_key = generate_ed25519_keypair_pem()
        key_ref = "did:example:node-2#fp-card"
        now = datetime.now(tz=timezone.utc)
        directory = DirectoryService(public_keys={key_ref: public_key}, require_signature=True)
        signed = sign_server_card(
            FPServerCard(
                card_id="card-2",
                entity_id="fp:agent:node-2",
                fp_version="0.1.0",
                rpc_url="https://node-2.example/rpc",
                well_known_url="https://node-2.example/.well-known/fp-server.json",
                issued_at=(now - timedelta(minutes=10)).isoformat().replace("+00:00", "Z"),
                expires_at=(now - timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
                ttl_seconds=60,
            ),
            private_key_pem=private_key,
            key_ref=key_ref,
            now=now - timedelta(minutes=10),
        )
        with self.assertRaises(FPError) as exc:
            directory.publish(signed, actor_ref="publisher")
        self.assertIs(exc.exception.code, FPErrorCode.NOT_FOUND)


if __name__ == "__main__":
    unittest.main()
