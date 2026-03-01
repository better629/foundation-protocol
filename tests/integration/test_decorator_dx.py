from __future__ import annotations

import unittest

from fp.app import FPServer, make_default_entity
from fp.app.decorators import operation
from fp.protocol import ActivityState, EntityKind


class DecoratorDXTests(unittest.TestCase):
    def test_typed_decorator_enables_schema_and_runtime_validation(self) -> None:
        server = FPServer()
        server.register_entity(make_default_entity("fp:agent:a", EntityKind.AGENT))
        server.register_entity(make_default_entity("fp:agent:b", EntityKind.AGENT))

        @operation("tool.multiply")
        def multiply(x: int, y: int) -> dict:
            return {"product": x * y}

        server.register_operation("tool.multiply", multiply)
        schema = server.dispatch.schema_for("tool.multiply")
        self.assertEqual(set(schema["required"]), {"x", "y"})

        session = server.sessions_create(
            participants={"fp:agent:a", "fp:agent:b"},
            roles={"fp:agent:a": {"caller"}, "fp:agent:b": {"tool"}},
        )
        ok = server.activities_start(
            session_id=session.session_id,
            owner_entity_id="fp:agent:b",
            initiator_entity_id="fp:agent:a",
            operation="tool.multiply",
            input_payload={"x": 3, "y": 7},
        )
        self.assertEqual(ok.state, ActivityState.COMPLETED)
        self.assertEqual(ok.result_payload, {"product": 21})

        invalid = server.activities_start(
            session_id=session.session_id,
            owner_entity_id="fp:agent:b",
            initiator_entity_id="fp:agent:a",
            operation="tool.multiply",
            input_payload={"x": "3", "y": 7},
        )
        self.assertEqual(invalid.state, ActivityState.FAILED)
        self.assertIn("INVALID_ARGUMENT", (invalid.error or {}).get("message", ""))


if __name__ == "__main__":
    unittest.main()
