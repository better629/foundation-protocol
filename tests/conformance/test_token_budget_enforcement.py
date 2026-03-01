from __future__ import annotations

import unittest

from fp.app import FPServer, make_default_entity
from fp.protocol import EntityKind, FPError, FPErrorCode, SessionBudget


class TokenBudgetEnforcementTests(unittest.TestCase):
    def test_activity_start_rejects_input_above_session_token_limit(self) -> None:
        server = FPServer()
        server.register_entity(make_default_entity("fp:agent:a", EntityKind.AGENT))
        server.register_entity(make_default_entity("fp:agent:b", EntityKind.AGENT))
        session = server.sessions_create(
            participants={"fp:agent:a", "fp:agent:b"},
            roles={"fp:agent:a": {"caller"}, "fp:agent:b": {"tool"}},
            budget=SessionBudget(token_limit=8),
        )
        server.register_operation("task.echo", lambda payload: payload)

        with self.assertRaises(FPError) as exc:
            server.activities_start(
                session_id=session.session_id,
                owner_entity_id="fp:agent:b",
                initiator_entity_id="fp:agent:a",
                operation="task.echo",
                input_payload={"text": "this payload is intentionally larger than the configured tiny budget"},
            )

        self.assertIs(exc.exception.code, FPErrorCode.RATE_LIMITED)
        details = exc.exception.details
        self.assertEqual(details["token_limit"], 8)
        self.assertGreater(details["estimated_input_tokens"], 8)


if __name__ == "__main__":
    unittest.main()
