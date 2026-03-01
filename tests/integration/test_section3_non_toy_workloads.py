from __future__ import annotations

import unittest

from fp.app import FPServer, make_default_entity
from fp.policy import PolicyContext, PolicyEngine, PolicyHook, allow, deny
from fp.protocol import EntityKind, FPError, FPErrorCode, Membership, Organization, OrganizationGovernance
from fp.quickstart import Agent


def _register(server: FPServer, entity_id: str, kind: EntityKind) -> None:
    server.register_entity(make_default_entity(entity_id, kind, display_name=entity_id))


class AllocationApprovalPolicy(PolicyEngine):
    def evaluate(self, context: PolicyContext):
        if context.hook is PolicyHook.PRE_INVOKE and context.operation == "allocation.finalize":
            if context.payload.get("approved") is not True:
                return deny("allocation.finalize requires explicit approval", policy_ref="policy:allocation-approval")
        return allow(policy_ref="policy:default")


class Section3NonToyWorkloads(unittest.TestCase):
    def test_high_volume_multi_entity_orchestration(self) -> None:
        server = FPServer()
        _register(server, "fp:agent:planner", EntityKind.AGENT)
        _register(server, "fp:resource:kb", EntityKind.RESOURCE)
        _register(server, "fp:ui:renderer", EntityKind.UI)
        tools = [f"fp:tool:t{i}" for i in range(1, 6)]
        for tool in tools:
            _register(server, tool, EntityKind.TOOL)

        participants = {"fp:agent:planner", "fp:resource:kb", "fp:ui:renderer", *tools}
        roles = {"fp:agent:planner": {"coordinator"}, "fp:resource:kb": {"provider"}, "fp:ui:renderer": {"renderer"}}
        for tool in tools:
            roles[tool] = {"provider"}
        session = server.sessions_create(participants=participants, roles=roles, policy_ref="policy:orchestration-v1")

        for tool in tools:
            op = f"{tool}.run"
            server.register_operation(op, lambda payload, tool_id=tool: {"tool": tool_id, "ok": True, "n": payload["n"]})
        server.register_operation("resource.fetch", lambda payload: {"resource_ref": payload["resource_ref"], "version": "v3"})
        server.register_operation("ui.render", lambda payload: {"frame_ref": f"ui://frame/{payload['n']}"})

        completed = 0
        for idx in range(30):
            tool_owner = tools[idx % len(tools)]
            activity = server.activities_start(
                session_id=session.session_id,
                owner_entity_id=tool_owner,
                initiator_entity_id="fp:agent:planner",
                operation=f"{tool_owner}.run",
                input_payload={"n": idx},
                idempotency_key=f"idem-tool-{idx}",
            )
            self.assertEqual(activity.state.value, "completed")
            completed += 1

        for idx in range(10):
            a_resource = server.activities_start(
                session_id=session.session_id,
                owner_entity_id="fp:resource:kb",
                initiator_entity_id="fp:agent:planner",
                operation="resource.fetch",
                input_payload={"resource_ref": f"kb://doc/{idx}"},
                idempotency_key=f"idem-resource-{idx}",
            )
            a_ui = server.activities_start(
                session_id=session.session_id,
                owner_entity_id="fp:ui:renderer",
                initiator_entity_id="fp:agent:planner",
                operation="ui.render",
                input_payload={"n": idx},
                idempotency_key=f"idem-ui-{idx}",
            )
            self.assertEqual(a_resource.state.value, "completed")
            self.assertEqual(a_ui.state.value, "completed")
            completed += 2

        stream = server.events_stream(session_id=session.session_id)
        events = server.events_read(stream_id=stream["stream_id"], limit=5000)
        server.events_ack(stream_id=stream["stream_id"], event_ids=[event.event_id for event in events])

        self.assertGreaterEqual(completed, 50)
        self.assertGreaterEqual(len(events), completed * 3)
        self.assertTrue(any(event.event_type == "activity.completed" for event in events))

    def test_long_running_workload_resubscribe_and_economy_closeout(self) -> None:
        server = FPServer()
        _register(server, "fp:agent:buyer", EntityKind.AGENT)
        _register(server, "fp:agent:seller", EntityKind.AGENT)
        session = server.sessions_create(
            participants={"fp:agent:buyer", "fp:agent:seller"},
            roles={"fp:agent:buyer": {"consumer"}, "fp:agent:seller": {"provider"}},
            policy_ref="policy:service-v2",
        )

        server.register_operation("service.provision", lambda _: {"state": "working"})
        activity = server.activities_start(
            session_id=session.session_id,
            owner_entity_id="fp:agent:seller",
            initiator_entity_id="fp:agent:buyer",
            operation="service.provision",
            input_payload={"workload": "gpu-train", "hours": 12},
        )
        self.assertEqual(activity.state.value, "working")

        push = server.push_config_set(
            {
                "push_config_id": "pcfg-service",
                "url": "https://hooks.example.com/fp/service",
                "scope": {"session_id": session.session_id, "activity_id": activity.activity_id},
                "auth": {"type": "bearer", "token_ref": "secret://hooks/service"},
                "event_types": ["service.progress", "activity.completed"],
            }
        )
        self.assertEqual(push["push_config_id"], "pcfg-service")

        for idx in range(120):
            server.emit_event(
                event_type="service.progress",
                session_id=session.session_id,
                activity_id=activity.activity_id,
                producer_entity_id="fp:agent:seller",
                payload={"step": idx, "percent": idx / 119.0},
            )

        stream = server.events_stream(session_id=session.session_id, activity_id=activity.activity_id)
        first = server.events_read(stream_id=stream["stream_id"], limit=50)
        server.events_ack(stream_id=stream["stream_id"], event_ids=[event.event_id for event in first])
        resumed = server.events_resubscribe(stream_id=stream["stream_id"], last_event_id=first[-1].event_id)
        second = server.events_read(stream_id=resumed["stream_id"], limit=500)

        completed = server.activities_complete(
            activity_id=activity.activity_id,
            result_payload={"deliverable_ref": "artifact://model/v2"},
            producer_entity_id="fp:agent:seller",
        )
        self.assertEqual(completed.state.value, "completed")

        meter = server.meter_record(
            subject_ref=activity.activity_id,
            unit="gpu-hour",
            quantity=12,
            metering_policy_ref="policy:gpu-meter",
        )
        receipt = server.receipts_issue(
            activity_id=activity.activity_id,
            provider_entity_id="fp:agent:seller",
            meter_records=[meter],
        )
        self.assertTrue(server.receipts.verify(receipt))

        settlement = server.settlements_create(
            receipt_refs=[receipt.receipt_id],
            settlement_ref="payment://network/txn-service-88",
            amount=88.5,
            currency="USD",
            actor_entity_id="fp:agent:buyer",
        )
        confirmed = server.settlements_confirm(settlement.settlement_id)

        self.assertGreaterEqual(len(first) + len(second), 121)
        self.assertEqual(confirmed.status.value, "confirmed")

    def test_governed_market_batch_settlement_and_dispute(self) -> None:
        server = FPServer(policy_engine=AllocationApprovalPolicy())
        org_entity = make_default_entity("fp:org:market", EntityKind.ORGANIZATION, "market")
        market = Organization(
            organization_id="fp:org:market",
            entity=org_entity,
            governance=OrganizationGovernance(
                policy_refs=["policy:market-governance"],
                role_catalog=["allocator", "bidder", "auditor"],
            ),
        )
        server.create_organization(market)

        _register(server, "fp:agent:allocator", EntityKind.AGENT)
        _register(server, "fp:agent:auditor", EntityKind.AGENT)
        bidders = [f"fp:agent:bidder-{i}" for i in range(1, 6)]
        for bidder in bidders:
            _register(server, bidder, EntityKind.AGENT)
            server.add_membership(
                Membership(
                    membership_id=f"mem-{bidder}",
                    organization_id=market.organization_id,
                    member_entity_id=bidder,
                    roles={"bidder"},
                ),
                actor_entity_id="fp:agent:auditor",
            )

        participants = {"fp:agent:allocator", "fp:agent:auditor", *bidders}
        roles = {"fp:agent:allocator": {"allocator"}, "fp:agent:auditor": {"auditor"}}
        for bidder in bidders:
            roles[bidder] = {"bidder"}
        session = server.sessions_create(participants=participants, roles=roles, policy_ref="policy:market-governance")

        price_board: dict[str, float] = {}
        for idx, bidder in enumerate(bidders):
            bid_price = 10.0 + idx * 1.25
            price_board[bidder] = bid_price
            server.emit_event(
                event_type="market.bid",
                session_id=session.session_id,
                producer_entity_id=bidder,
                payload={"resource": "gpu-hour", "price": bid_price},
            )
        winner = max(price_board, key=price_board.get)

        server.register_operation("allocation.finalize", lambda payload: {"winner": payload["winner"], "price": payload["price"]})

        with self.assertRaises(FPError) as denied:
            server.activities_start(
                session_id=session.session_id,
                owner_entity_id="fp:agent:allocator",
                initiator_entity_id="fp:agent:allocator",
                operation="allocation.finalize",
                input_payload={"winner": winner, "price": price_board[winner]},
            )
        self.assertIs(denied.exception.code, FPErrorCode.POLICY_DENIED)

        approved = server.activities_start(
            session_id=session.session_id,
            owner_entity_id="fp:agent:allocator",
            initiator_entity_id="fp:agent:allocator",
            operation="allocation.finalize",
            input_payload={"winner": winner, "price": price_board[winner], "approved": True},
        )
        self.assertEqual(approved.state.value, "completed")

        meter_records = [
            server.meter_record(subject_ref=approved.activity_id, unit="token", quantity=3_000, metering_policy_ref="policy:meter"),
            server.meter_record(subject_ref=approved.activity_id, unit="call", quantity=1, metering_policy_ref="policy:meter"),
        ]
        receipt = server.receipts_issue(
            activity_id=approved.activity_id,
            provider_entity_id="fp:agent:allocator",
            meter_records=meter_records,
        )
        settlement = server.settlements_create(
            receipt_refs=[receipt.receipt_id],
            settlement_ref="payment://market/txn-998",
            amount=price_board[winner],
            currency="USD",
            actor_entity_id=winner,
        )
        confirmed = server.settlements_confirm(settlement.settlement_id)
        dispute = server.disputes_open(
            target_ref=receipt.receipt_id,
            reason_code="price-disagreement",
            claimant_entity_id=bidders[0],
            evidence_refs=["evidence://market/bid-log-1"],
        )

        self.assertTrue(server.receipts.verify(receipt))
        self.assertEqual(confirmed.status.value, "confirmed")
        self.assertEqual(dispute.status, "open")
        outcomes = {record.outcome for record in server.provenance_list()}
        self.assertIn("denied", outcomes)
        self.assertIn("allowed", outcomes)

    def test_framework_embedding_with_shared_fp_runtime(self) -> None:
        shared_server = FPServer()
        planner = Agent(entity_id="fp:agent:planner-sdk", server=shared_server)
        worker = Agent(entity_id="fp:agent:worker-sdk", server=shared_server)

        @worker.activity("task.summarize")
        def summarize(payload: dict) -> dict:
            text = payload["text"]
            return {"summary": text[:20], "length": len(text)}

        session = planner.start_session(
            participants={planner.entity_id, worker.entity_id},
            roles={planner.entity_id: {"coordinator"}, worker.entity_id: {"provider"}},
            policy_ref="policy:sdk-embed",
        )
        activity = planner.start_activity(
            session_id=session.session_id,
            operation="task.summarize",
            owner_entity_id=worker.entity_id,
            input_payload={"text": "foundation protocol integrates with agent frameworks cleanly"},
        )

        self.assertEqual(activity.state.value, "completed")
        self.assertIn("summary", activity.result_payload or {})


if __name__ == "__main__":
    unittest.main()
