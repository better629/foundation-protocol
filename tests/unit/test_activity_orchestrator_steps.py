from __future__ import annotations

import unittest

from fp.app import FPServer, make_default_entity
from fp.policy import PolicyHook, allow, deny
from fp.protocol import FPError, FPErrorCode, SessionBudget, SessionState, EntityKind


class _DenyPreInvokePolicy:
    def evaluate(self, context):
        if context.hook is PolicyHook.PRE_INVOKE:
            return deny("invoke denied", policy_ref="policy:test:deny")
        return allow("ok", policy_ref="policy:test:allow")


def _bootstrap_server(*, policy_engine=None, budget: SessionBudget | None = None) -> tuple[FPServer, str]:
    server = FPServer(policy_engine=policy_engine)
    server.register_entity(make_default_entity("fp:agent:a", EntityKind.AGENT))
    server.register_entity(make_default_entity("fp:agent:b", EntityKind.AGENT))
    session = server.sessions_create(
        participants={"fp:agent:a", "fp:agent:b"},
        roles={"fp:agent:a": {"coordinator"}, "fp:agent:b": {"worker"}},
        budget=budget,
    )
    return server, session.session_id


class ActivityOrchestratorStepTests(unittest.TestCase):
    def test_precheck_rejects_non_active_session(self) -> None:
        server, session_id = _bootstrap_server()
        server.sessions_update(session_id=session_id, state=SessionState.PAUSED)

        with self.assertRaises(FPError) as exc:
            server.activities_start(
                session_id=session_id,
                owner_entity_id="fp:agent:b",
                initiator_entity_id="fp:agent:a",
                operation="task.noop",
                input_payload={},
                auto_execute=False,
            )
        self.assertIs(exc.exception.code, FPErrorCode.INVALID_STATE_TRANSITION)

    def test_precheck_rejects_owner_outside_participants(self) -> None:
        server, session_id = _bootstrap_server()
        server.register_entity(make_default_entity("fp:agent:c", EntityKind.AGENT))

        with self.assertRaises(FPError) as exc:
            server.activities_start(
                session_id=session_id,
                owner_entity_id="fp:agent:c",
                initiator_entity_id="fp:agent:a",
                operation="task.noop",
                input_payload={},
                auto_execute=False,
            )
        self.assertIs(exc.exception.code, FPErrorCode.AUTHZ_DENIED)

    def test_budget_guard_blocks_oversized_payload(self) -> None:
        server, session_id = _bootstrap_server(budget=SessionBudget(token_limit=1))

        with self.assertRaises(FPError) as exc:
            server.activities_start(
                session_id=session_id,
                owner_entity_id="fp:agent:b",
                initiator_entity_id="fp:agent:a",
                operation="task.noop",
                input_payload={"payload": "12345678901234567890"},
                auto_execute=False,
            )
        self.assertIs(exc.exception.code, FPErrorCode.RATE_LIMITED)

    def test_idempotency_reuses_activity_without_reexecution(self) -> None:
        server, session_id = _bootstrap_server()
        calls = {"count": 0}

        def handler(payload: dict) -> dict:
            calls["count"] += 1
            return {"echo": payload.get("v")}

        server.register_operation("task.echo", handler)

        first = server.activities_start(
            session_id=session_id,
            owner_entity_id="fp:agent:b",
            initiator_entity_id="fp:agent:a",
            operation="task.echo",
            input_payload={"v": 7},
            idempotency_key="idem-orch",
            auto_execute=True,
        )
        second = server.activities_start(
            session_id=session_id,
            owner_entity_id="fp:agent:b",
            initiator_entity_id="fp:agent:a",
            operation="task.echo",
            input_payload={"v": 7},
            idempotency_key="idem-orch",
            auto_execute=True,
        )

        self.assertEqual(calls["count"], 1)
        self.assertEqual(first.activity_id, second.activity_id)

    def test_policy_gate_denies_before_activity_creation(self) -> None:
        server, session_id = _bootstrap_server(policy_engine=_DenyPreInvokePolicy())

        with self.assertRaises(FPError) as exc:
            server.activities_start(
                session_id=session_id,
                owner_entity_id="fp:agent:b",
                initiator_entity_id="fp:agent:a",
                operation="task.noop",
                input_payload={"x": 1},
                auto_execute=False,
            )
        self.assertIs(exc.exception.code, FPErrorCode.POLICY_DENIED)
        self.assertEqual(server.activities_list(session_id=session_id), [])

    def test_auto_execution_emits_completion_and_failure_events(self) -> None:
        server, session_id = _bootstrap_server()

        server.register_operation("task.ok", lambda payload: {"result": payload["x"]})

        def boom(_: dict) -> dict:
            raise RuntimeError("boom")

        server.register_operation("task.fail", boom)

        completed = server.activities_start(
            session_id=session_id,
            owner_entity_id="fp:agent:b",
            initiator_entity_id="fp:agent:a",
            operation="task.ok",
            input_payload={"x": 9},
            activity_id="act-completed",
            auto_execute=True,
        )
        failed = server.activities_start(
            session_id=session_id,
            owner_entity_id="fp:agent:b",
            initiator_entity_id="fp:agent:a",
            operation="task.fail",
            input_payload={"x": 0},
            activity_id="act-failed",
            auto_execute=True,
        )

        stream = server.events_stream(session_id=session_id)
        events = server.events_read(stream_id=stream["stream_id"], limit=200)
        completed_events = [event.event_type for event in events if event.activity_id == completed.activity_id]
        failed_events = [event.event_type for event in events if event.activity_id == failed.activity_id]

        self.assertEqual(completed.state.value, "completed")
        self.assertEqual(failed.state.value, "failed")
        self.assertEqual(completed_events, ["activity.submitted", "activity.working", "activity.completed"])
        self.assertEqual(failed_events, ["activity.submitted", "activity.working", "activity.failed"])


if __name__ == "__main__":
    unittest.main()
