from __future__ import annotations

import unittest

from fp.app import FPServer, make_default_entity
from fp.protocol import ActivityState, EntityKind


class ContextCompactionFlowTests(unittest.TestCase):
    def test_large_activity_result_is_compacted_with_deterministic_result_ref(self) -> None:
        server = FPServer()
        server.set_result_compaction(max_inline_bytes=200, preview_chars=60)
        server.register_entity(make_default_entity("fp:agent:a", EntityKind.AGENT))
        server.register_entity(make_default_entity("fp:agent:b", EntityKind.AGENT))
        session = server.sessions_create(
            participants={"fp:agent:a", "fp:agent:b"},
            roles={"fp:agent:a": {"caller"}, "fp:agent:b": {"worker"}},
        )
        server.register_operation(
            "task.large",
            lambda payload: {"blob": "x" * 5000, "request_id": payload["request_id"]},
        )

        activity = server.activities_start(
            session_id=session.session_id,
            owner_entity_id="fp:agent:b",
            initiator_entity_id="fp:agent:a",
            operation="task.large",
            input_payload={"request_id": "req-1"},
        )

        self.assertEqual(activity.state, ActivityState.COMPLETED)
        self.assertIsNotNone(activity.result_ref)
        self.assertTrue((activity.result_ref or "").startswith("sha256://"))
        self.assertIsNotNone(activity.result_payload)
        self.assertEqual(activity.result_payload["compacted"], True)
        self.assertGreater(activity.result_payload["bytes"], 200)

        result = server.activities_result(activity_id=activity.activity_id)
        self.assertEqual(result["result_ref"], activity.result_ref)
        self.assertEqual(result["result"]["compacted"], True)


if __name__ == "__main__":
    unittest.main()
