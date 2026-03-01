from __future__ import annotations

import unittest

from fp.app import FPServer, make_default_entity
from fp.protocol import EntityKind
from fp.protocol import FPErrorCode
from fp.transport.http_jsonrpc import JSONRPCDispatcher


class JSONRPCTransportTests(unittest.TestCase):
    def test_ping_request_roundtrip(self) -> None:
        server = FPServer()
        dispatcher = JSONRPCDispatcher.from_server(server)

        response = dispatcher.handle(
            {
                "jsonrpc": "2.0",
                "id": "1",
                "method": "fp/ping",
                "params": {},
            }
        )

        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], "1")
        self.assertEqual(response["result"]["ok"], True)
        self.assertEqual(response["result"]["fp_version"], "0.1.0")

    def test_notification_returns_none(self) -> None:
        server = FPServer()
        dispatcher = JSONRPCDispatcher.from_server(server)

        response = dispatcher.handle(
            {
                "jsonrpc": "2.0",
                "method": "fp/ping",
                "params": {},
            }
        )
        self.assertIsNone(response)

    def test_invalid_request_returns_jsonrpc_error(self) -> None:
        server = FPServer()
        dispatcher = JSONRPCDispatcher.from_server(server)

        response = dispatcher.handle({"id": "bad", "method": "fp/ping"})
        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response["error"]["code"], -32600)

    def test_fp_error_is_mapped_into_error_data(self) -> None:
        server = FPServer()
        dispatcher = JSONRPCDispatcher.from_server(server)

        response = dispatcher.handle(
            {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "fp/sessions.get",
                "params": {"session_id": "sess-missing"},
            }
        )

        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response["error"]["code"], -32000)
        self.assertEqual(response["error"]["data"]["fp"]["code"], FPErrorCode.NOT_FOUND.value)

    def test_dispatcher_supports_core_session_methods(self) -> None:
        server = FPServer()
        server.register_entity(make_default_entity("fp:agent:a", EntityKind.AGENT))
        server.register_entity(make_default_entity("fp:agent:b", EntityKind.AGENT))
        dispatcher = JSONRPCDispatcher.from_server(server)

        created = dispatcher.handle(
            {
                "jsonrpc": "2.0",
                "id": "c1",
                "method": "fp/sessions.create",
                "params": {
                    "participants": ["fp:agent:a", "fp:agent:b"],
                    "roles": {"fp:agent:a": ["coordinator"], "fp:agent:b": ["worker"]},
                },
            }
        )
        self.assertIsNotNone(created)
        assert created is not None
        session_id = created["result"]["session_id"]

        got = dispatcher.handle(
            {
                "jsonrpc": "2.0",
                "id": "g1",
                "method": "fp/sessions.get",
                "params": {"params": {"sessionId": session_id}},
            }
        )
        self.assertIsNotNone(got)
        assert got is not None
        self.assertEqual(got["result"]["session_id"], session_id)

    def test_activities_start_requires_non_empty_operation(self) -> None:
        server = FPServer()
        server.register_entity(make_default_entity("fp:agent:a", EntityKind.AGENT))
        server.register_entity(make_default_entity("fp:agent:b", EntityKind.AGENT))
        session = server.sessions_create(
            participants={"fp:agent:a", "fp:agent:b"},
            roles={"fp:agent:a": {"coordinator"}, "fp:agent:b": {"worker"}},
        )
        dispatcher = JSONRPCDispatcher.from_server(server)

        response = dispatcher.handle(
            {
                "jsonrpc": "2.0",
                "id": "bad-op",
                "method": "fp/activities.start",
                "params": {
                    "session_id": session.session_id,
                    "owner_entity_id": "fp:agent:b",
                    "initiator_entity_id": "fp:agent:a",
                    "input_payload": {"q": "x"},
                },
            }
        )
        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response["error"]["code"], -32602)

    def test_push_config_set_rejects_malformed_payload(self) -> None:
        server = FPServer()
        dispatcher = JSONRPCDispatcher.from_server(server)

        response = dispatcher.handle(
            {
                "jsonrpc": "2.0",
                "id": "bad-push",
                "method": "fp/events.pushConfig.set",
                "params": {
                    "config": {
                        "push_config_id": "pcfg-1",
                        "scope": {"session_id": "sess-1"},
                    }
                },
            }
        )
        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response["error"]["code"], -32602)


if __name__ == "__main__":
    unittest.main()
