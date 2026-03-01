from __future__ import annotations

import unittest

from fp.app import FPServer, make_default_entity
from fp.protocol import EntityKind


class ServerFacadeParityTests(unittest.TestCase):
    def test_server_exposes_runtime_modules(self) -> None:
        server = FPServer()
        self.assertIsNotNone(server.runtime)
        self.assertIsNotNone(server.graph)
        self.assertIsNotNone(server.session_module)
        self.assertIsNotNone(server.activity_module)
        self.assertIsNotNone(server.event_module)
        self.assertIsNotNone(server.economy_module)
        self.assertIsNotNone(server.governance_module)

    def test_facade_behavior_remains_stable(self) -> None:
        server = FPServer()
        server.register_entity(make_default_entity("fp:agent:a", EntityKind.AGENT))
        server.register_entity(make_default_entity("fp:agent:b", EntityKind.AGENT))
        server.register_operation("task.echo", lambda payload: {"echo": payload["v"]})

        session = server.sessions_create(
            participants={"fp:agent:a", "fp:agent:b"},
            roles={"fp:agent:a": {"coordinator"}, "fp:agent:b": {"worker"}},
        )
        activity = server.activities_start(
            session_id=session.session_id,
            owner_entity_id="fp:agent:b",
            initiator_entity_id="fp:agent:a",
            operation="task.echo",
            input_payload={"v": 123},
        )
        self.assertEqual(activity.state.value, "completed")
        self.assertEqual(activity.result_payload, {"echo": 123})


if __name__ == "__main__":
    unittest.main()
