from __future__ import annotations

import unittest

from fp.app import FPClient, FPServer, make_default_entity
from fp.protocol import EntityKind
from fp.transport import FPHTTPPublishedServer


class ClientRemoteInteropTests(unittest.TestCase):
    def test_client_can_call_remote_published_server(self) -> None:
        server = FPServer(server_entity_id="fp:system:remote")
        server.register_entity(make_default_entity("fp:agent:a", EntityKind.AGENT))
        server.register_entity(make_default_entity("fp:agent:b", EntityKind.AGENT))
        server.register_operation("task.quote", lambda payload: {"price": payload["price"]})

        with FPHTTPPublishedServer(server, publish_entity_id="fp:agent:b", host="127.0.0.1", port=0) as published:
            client = FPClient.from_http_jsonrpc(published.rpc_url)
            ping = client.ping()
            self.assertEqual(ping["ok"], True)

            session = client.session_create(
                participants={"fp:agent:a", "fp:agent:b"},
                roles={"fp:agent:a": {"consumer"}, "fp:agent:b": {"provider"}},
            )
            activity = client.activity_start(
                session_id=session["session_id"],
                owner_entity_id="fp:agent:b",
                initiator_entity_id="fp:agent:a",
                operation="task.quote",
                input_payload={"price": 99.5},
            )
            self.assertEqual(activity["state"], "completed")
            self.assertEqual(activity["result_payload"]["price"], 99.5)


if __name__ == "__main__":
    unittest.main()
