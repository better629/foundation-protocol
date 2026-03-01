from __future__ import annotations

import unittest

from fp.app import FPServer, make_default_entity
from fp.federation import FPServerCard, InMemoryDirectory, NetworkResolver, RemoteFPClient, fetch_server_card
from fp.protocol import EntityKind, FPError, FPErrorCode
from fp.transport.http_publish import FPHTTPPublishedServer


class FederationNetworkTests(unittest.TestCase):
    def test_publish_discover_connect_and_trade_over_http(self) -> None:
        seller_server = FPServer(server_entity_id="fp:system:seller")
        seller_server.register_entity(make_default_entity("fp:agent:buyer", EntityKind.AGENT))
        seller_server.register_entity(make_default_entity("fp:agent:seller", EntityKind.AGENT))
        seller_server.register_operation("trade.quote", lambda payload: {"asset": payload["asset"], "price": 42.0})

        directory = InMemoryDirectory()
        with FPHTTPPublishedServer(
            seller_server,
            publish_entity_id="fp:agent:seller",
            host="127.0.0.1",
            port=0,
        ) as published:
            card = fetch_server_card(published.well_known_url)
            directory.publish(card)
            resolver = NetworkResolver(directory)
            client = resolver.connect("fp:agent:seller")

            ping = client.call("fp/ping", {})
            self.assertEqual(ping["ok"], True)

            session = client.call(
                "fp/sessions.create",
                {
                    "participants": ["fp:agent:buyer", "fp:agent:seller"],
                    "roles": {"fp:agent:buyer": ["consumer"], "fp:agent:seller": ["provider"]},
                },
            )
            activity = client.call(
                "fp/activities.start",
                {
                    "session_id": session["session_id"],
                    "owner_entity_id": "fp:agent:seller",
                    "initiator_entity_id": "fp:agent:buyer",
                    "operation": "trade.quote",
                    "input_payload": {"asset": "gpu-hour"},
                },
            )
            self.assertEqual(activity["state"], "completed")
            self.assertEqual(activity["result_payload"]["price"], 42.0)

    def test_directory_rejects_duplicate_entity_publication(self) -> None:
        directory = InMemoryDirectory()
        card = FPServerCard(
            card_id="card-1",
            entity_id="fp:agent:x",
            fp_version="0.1.0",
            rpc_url="http://127.0.0.1:9001/rpc",
            well_known_url="http://127.0.0.1:9001/.well-known/fp-server.json",
        )
        directory.publish(card)
        with self.assertRaises(FPError) as exc:
            directory.publish(card)
        self.assertIs(exc.exception.code, FPErrorCode.ALREADY_EXISTS)

    def test_remote_client_raises_structured_fp_error(self) -> None:
        server = FPServer()
        with FPHTTPPublishedServer(server, publish_entity_id="fp:agent:server", host="127.0.0.1", port=0) as published:
            card = fetch_server_card(published.well_known_url)
            client = RemoteFPClient(card.rpc_url)
            with self.assertRaises(FPError) as exc:
                client.call("fp/sessions.get", {"session_id": "sess-missing"})
            self.assertIs(exc.exception.code, FPErrorCode.NOT_FOUND)


if __name__ == "__main__":
    unittest.main()
