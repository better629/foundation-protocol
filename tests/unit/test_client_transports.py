from __future__ import annotations

import unittest

from fp.app import FPClient, FPServer, make_default_entity
from fp.protocol import EntityKind


def _sid(value):
    if isinstance(value, dict):
        return value["session_id"]
    return value.session_id


def _activity_state(value):
    if isinstance(value, dict):
        return value["state"]
    return value.state.value


class ClientTransportTests(unittest.TestCase):
    def test_from_inproc_transport_roundtrip(self) -> None:
        server = FPServer()
        server.register_entity(make_default_entity("fp:agent:a", EntityKind.AGENT))
        server.register_entity(make_default_entity("fp:agent:b", EntityKind.AGENT))
        server.register_operation("task.echo", lambda payload: {"echo": payload["x"]})

        client = FPClient.from_inproc(server)
        session = client.session_create(
            participants={"fp:agent:a", "fp:agent:b"},
            roles={"fp:agent:a": {"coordinator"}, "fp:agent:b": {"worker"}},
        )
        activity = client.activity_start(
            session_id=_sid(session),
            owner_entity_id="fp:agent:b",
            initiator_entity_id="fp:agent:a",
            operation="task.echo",
            input_payload={"x": "ok"},
        )

        self.assertEqual(_activity_state(activity), "completed")


if __name__ == "__main__":
    unittest.main()
