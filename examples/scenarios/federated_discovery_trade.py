from __future__ import annotations

from fp.app import FPServer, make_default_entity
from fp.federation import InMemoryDirectory, NetworkResolver, fetch_server_card
from fp.protocol import EntityKind
from fp.transport import FPHTTPPublishedServer


def run_example() -> dict:
    seller_server = FPServer(server_entity_id="fp:system:seller")
    seller_server.register_entity(make_default_entity("fp:agent:seller", EntityKind.AGENT))
    seller_server.register_entity(make_default_entity("fp:agent:buyer", EntityKind.AGENT))
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
        client = NetworkResolver(directory).connect("fp:agent:seller")

        ping = client.ping()
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
        return {
            "ping_ok": ping["ok"],
            "session_id": session["session_id"],
            "state": activity["state"],
            "price": activity["result_payload"]["price"],
            "rpc_url": card.rpc_url,
        }


if __name__ == "__main__":
    print(run_example())
