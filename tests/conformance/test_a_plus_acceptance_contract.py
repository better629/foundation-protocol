from __future__ import annotations

import unittest

from fp.app import FPClient, FPServer
from fp.federation import FPServerCard


class APlusAcceptanceContractTests(unittest.TestCase):
    def test_transport_backed_client_factories_exist(self) -> None:
        self.assertTrue(hasattr(FPClient, "from_inproc"))
        self.assertTrue(hasattr(FPClient, "from_http_jsonrpc"))

    def test_async_surfaces_exist(self) -> None:
        from fp.app.async_client import AsyncFPClient  # noqa: PLC0415
        from fp.app.async_server import AsyncFPServer  # noqa: PLC0415

        server = AsyncFPServer()
        client = AsyncFPClient.from_inproc(server)
        self.assertIsNotNone(client)

    def test_federation_card_signature_and_ttl_fields_exist(self) -> None:
        card = FPServerCard(
            card_id="card-1",
            entity_id="fp:agent:test",
            fp_version="0.1.0",
            rpc_url="https://fp.example/rpc",
            well_known_url="https://fp.example/.well-known/fp-server.json",
            sign_alg="ed25519",
            key_ref="did:example:fp#key-1",
            signature="sig-abc",
            issued_at="2026-03-01T00:00:00Z",
            expires_at="2026-03-01T00:10:00Z",
            ttl_seconds=600,
        )
        payload = card.to_dict()
        self.assertEqual(payload["sign_alg"], "ed25519")
        self.assertEqual(payload["key_ref"], "did:example:fp#key-1")
        self.assertEqual(payload["ttl_seconds"], 600)

    def test_server_exposes_token_budget_enforcer_hook(self) -> None:
        server = FPServer()
        self.assertTrue(hasattr(server, "set_token_budget_enforcer"))


if __name__ == "__main__":
    unittest.main()
