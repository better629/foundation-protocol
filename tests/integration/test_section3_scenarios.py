from __future__ import annotations

import unittest

from fp.app import FPServer, make_default_entity
from fp.policy import PolicyContext, PolicyEngine, PolicyHook, allow, deny
from fp.protocol import EntityKind, FPError, FPErrorCode, Membership, Organization, OrganizationGovernance


class ApprovalPolicyEngine(PolicyEngine):
    def evaluate(self, context: PolicyContext):
        if context.hook is PolicyHook.PRE_INVOKE and context.operation == "funds.transfer":
            if context.payload.get("approved_by") != "fp:human:reviewer":
                return deny("high-risk transfer requires reviewer approval", policy_ref="policy:transfer-approval")
        return allow(policy_ref="policy:default")


def _register(server: FPServer, entity_id: str, kind: EntityKind):
    server.register_entity(make_default_entity(entity_id, kind, display_name=entity_id))


class Section3ScenarioTests(unittest.TestCase):
    def test_section_3_1_daily_work_tools_agents_ui(self) -> None:
        server = FPServer()
        _register(server, "fp:agent:assistant", EntityKind.AGENT)
        _register(server, "fp:tool:search", EntityKind.TOOL)
        _register(server, "fp:resource:kb", EntityKind.RESOURCE)
        _register(server, "fp:ui:renderer", EntityKind.UI)

        session = server.sessions_create(
            participants={"fp:agent:assistant", "fp:tool:search", "fp:resource:kb", "fp:ui:renderer"},
            roles={
                "fp:agent:assistant": {"coordinator"},
                "fp:tool:search": {"provider"},
                "fp:resource:kb": {"provider"},
                "fp:ui:renderer": {"renderer"},
            },
            policy_ref="policy:daily-work",
        )

        server.register_operation("tool.search", lambda payload: {"hits": [payload["query"]]})
        server.register_operation("resource.read", lambda payload: {"resource_ref": payload["resource_ref"], "content": "ok"})
        server.register_operation("ui.render", lambda payload: {"frame_ref": f"ui://{payload['template']}"})

        a1 = server.activities_start(
            session_id=session.session_id,
            owner_entity_id="fp:tool:search",
            initiator_entity_id="fp:agent:assistant",
            operation="tool.search",
            input_payload={"query": "FP architecture"},
        )
        a2 = server.activities_start(
            session_id=session.session_id,
            owner_entity_id="fp:resource:kb",
            initiator_entity_id="fp:agent:assistant",
            operation="resource.read",
            input_payload={"resource_ref": "kb://policy"},
        )
        a3 = server.activities_start(
            session_id=session.session_id,
            owner_entity_id="fp:ui:renderer",
            initiator_entity_id="fp:agent:assistant",
            operation="ui.render",
            input_payload={"template": "summary-card"},
        )

        self.assertEqual(a1.state.value, "completed")
        self.assertEqual(a2.state.value, "completed")
        self.assertEqual(a3.state.value, "completed")

        stream = server.events_stream(session_id=session.session_id)
        events = server.events_read(stream_id=stream["stream_id"], limit=200)
        event_types = [event.event_type for event in events]

        self.assertIn("activity.completed", event_types)
        self.assertTrue(all(event.session_id == session.session_id for event in events))

        server.events_ack(stream_id=stream["stream_id"], event_ids=[event.event_id for event in events])

    def test_section_3_2_forming_and_operating_ai_organization(self) -> None:
        server = FPServer(policy_engine=ApprovalPolicyEngine())

        org_entity = make_default_entity("fp:org:ops", EntityKind.ORGANIZATION, "ops")
        org = Organization(
            organization_id="fp:org:ops",
            entity=org_entity,
            governance=OrganizationGovernance(
                policy_refs=["policy:org-governance"],
                role_catalog=["operator", "reviewer", "treasurer"],
            ),
        )
        server.create_organization(org)

        _register(server, "fp:agent:treasurer", EntityKind.AGENT)
        _register(server, "fp:human:reviewer", EntityKind.HUMAN)

        server.add_membership(
            Membership(
                membership_id="mem-treasurer",
                organization_id=org.organization_id,
                member_entity_id="fp:agent:treasurer",
                roles={"treasurer"},
            ),
            actor_entity_id="fp:human:reviewer",
        )
        server.add_membership(
            Membership(
                membership_id="mem-reviewer",
                organization_id=org.organization_id,
                member_entity_id="fp:human:reviewer",
                roles={"reviewer"},
            ),
            actor_entity_id="fp:human:reviewer",
        )

        session = server.sessions_create(
            participants={"fp:agent:treasurer", "fp:human:reviewer"},
            roles={"fp:agent:treasurer": {"treasurer"}, "fp:human:reviewer": {"reviewer"}},
            policy_ref="policy:org-governance",
        )

        server.register_operation("funds.transfer", lambda payload: {"transfer": "ok", "amount": payload["amount"]})

        with self.assertRaises(FPError) as denied:
            server.activities_start(
                session_id=session.session_id,
                owner_entity_id="fp:agent:treasurer",
                initiator_entity_id="fp:agent:treasurer",
                operation="funds.transfer",
                input_payload={"amount": 1000},
            )
        self.assertIs(denied.exception.code, FPErrorCode.POLICY_DENIED)

        activity = server.activities_start(
            session_id=session.session_id,
            owner_entity_id="fp:agent:treasurer",
            initiator_entity_id="fp:agent:treasurer",
            operation="funds.transfer",
            input_payload={"amount": 1000, "approved_by": "fp:human:reviewer"},
        )
        self.assertEqual(activity.state.value, "completed")

        outcomes = {record.outcome for record in server.provenance_list()}
        self.assertIn("denied", outcomes)
        self.assertIn("allowed", outcomes)

    def test_section_3_3_procurement_and_service_relationship(self) -> None:
        server = FPServer()
        _register(server, "fp:agent:buyer", EntityKind.AGENT)
        _register(server, "fp:agent:seller", EntityKind.AGENT)

        session = server.sessions_create(
            participants={"fp:agent:buyer", "fp:agent:seller"},
            roles={"fp:agent:buyer": {"consumer"}, "fp:agent:seller": {"provider"}},
            policy_ref="policy:procurement",
        )

        server.register_operation("service.provision", lambda _: {"state": "working"})

        activity = server.activities_start(
            session_id=session.session_id,
            owner_entity_id="fp:agent:seller",
            initiator_entity_id="fp:agent:buyer",
            operation="service.provision",
            input_payload={"terms_ref": "terms://signed/v1"},
        )
        self.assertEqual(activity.state.value, "working")

        server.emit_event(
            event_type="provision.progress",
            session_id=session.session_id,
            activity_id=activity.activity_id,
            producer_entity_id="fp:agent:seller",
            payload={"milestone": "halfway"},
        )
        server.emit_event(
            event_type="provision.compliance",
            session_id=session.session_id,
            activity_id=activity.activity_id,
            producer_entity_id="fp:agent:seller",
            payload={"checkpoint": "policy-ok"},
        )

        completed = server.activities_complete(
            activity_id=activity.activity_id,
            result_ref="deliverable://svc/alpha",
            producer_entity_id="fp:agent:seller",
        )
        self.assertEqual(completed.state.value, "completed")

        meter = server.meter_record(
            subject_ref=activity.activity_id,
            unit="call",
            quantity=1,
            metering_policy_ref="policy:metering",
        )
        receipt = server.receipts_issue(
            activity_id=activity.activity_id,
            provider_entity_id="fp:agent:seller",
            meter_records=[meter],
        )
        self.assertTrue(server.receipts.verify(receipt))

        settlement = server.settlements_create(
            receipt_refs=[receipt.receipt_id],
            settlement_ref="payment://network/txn-001",
            amount=49.99,
            currency="USD",
            actor_entity_id="fp:agent:buyer",
        )
        confirmed = server.settlements_confirm(settlement.settlement_id)
        self.assertEqual(confirmed.status.value, "confirmed")

    def test_section_3_4_market_resource_allocation(self) -> None:
        server = FPServer()
        _register(server, "fp:agent:auctioneer", EntityKind.AGENT)
        _register(server, "fp:agent:bidder-a", EntityKind.AGENT)
        _register(server, "fp:agent:bidder-b", EntityKind.AGENT)

        session = server.sessions_create(
            participants={"fp:agent:auctioneer", "fp:agent:bidder-a", "fp:agent:bidder-b"},
            roles={
                "fp:agent:auctioneer": {"allocator"},
                "fp:agent:bidder-a": {"bidder"},
                "fp:agent:bidder-b": {"bidder"},
            },
            policy_ref="policy:market-auction",
        )

        server.emit_event(
            event_type="market.bid",
            session_id=session.session_id,
            producer_entity_id="fp:agent:bidder-a",
            payload={"price": 12.5, "resource": "gpu-hour"},
        )
        server.emit_event(
            event_type="market.bid",
            session_id=session.session_id,
            producer_entity_id="fp:agent:bidder-b",
            payload={"price": 15.0, "resource": "gpu-hour"},
        )
        server.emit_event(
            event_type="market.allocated",
            session_id=session.session_id,
            producer_entity_id="fp:agent:auctioneer",
            payload={"winner": "fp:agent:bidder-b", "price": 15.0},
        )

        meter = server.meter_record(
            subject_ref=session.session_id,
            unit="call",
            quantity=1,
            metering_policy_ref="policy:market-meter",
        )
        activity = server.activities_start(
            session_id=session.session_id,
            owner_entity_id="fp:agent:auctioneer",
            initiator_entity_id="fp:agent:auctioneer",
            operation="noop",
            input_payload={},
            auto_execute=False,
        )
        receipt = server.receipts_issue(
            activity_id=activity.activity_id,
            provider_entity_id="fp:agent:auctioneer",
            meter_records=[meter],
        )
        settlement = server.settlements_create(
            receipt_refs=[receipt.receipt_id],
            settlement_ref="payment://market/txn-9",
            amount=15.0,
            currency="USD",
        )

        stream = server.events_stream(session_id=session.session_id)
        events = server.events_read(stream_id=stream["stream_id"], limit=100)
        ordered_types = [event.event_type for event in events]
        self.assertLess(ordered_types.index("market.bid"), ordered_types.index("market.allocated"))
        self.assertEqual(settlement.amount, 15.0)

    def test_section_3_5_social_network_and_collective_governance(self) -> None:
        server = FPServer()
        _register(server, "fp:org:community", EntityKind.ORGANIZATION)
        _register(server, "fp:agent:user-a", EntityKind.AGENT)
        _register(server, "fp:agent:moderator", EntityKind.AGENT)

        org = Organization(
            organization_id="fp:org:community",
            entity=make_default_entity("fp:org:community", EntityKind.ORGANIZATION, "community"),
            governance=OrganizationGovernance(
                policy_refs=["policy:community-v1"],
                role_catalog=["member", "moderator", "auditor"],
            ),
        )
        server.create_organization(org)
        server.add_membership(
            Membership(
                membership_id="mem-user-a",
                organization_id=org.organization_id,
                member_entity_id="fp:agent:user-a",
                roles={"member"},
            )
        )
        server.add_membership(
            Membership(
                membership_id="mem-moderator",
                organization_id=org.organization_id,
                member_entity_id="fp:agent:moderator",
                roles={"moderator"},
            )
        )

        session = server.sessions_create(
            participants={"fp:agent:user-a", "fp:agent:moderator"},
            roles={"fp:agent:user-a": {"member"}, "fp:agent:moderator": {"moderator"}},
            policy_ref="policy:community-v1",
        )

        post_event = server.emit_event(
            event_type="social.posted",
            session_id=session.session_id,
            producer_entity_id="fp:agent:user-a",
            payload={"post_ref": "post://123", "text_digest": "sha256:abc"},
        )

        dispute = server.disputes_open(
            target_ref=post_event.event_id,
            reason_code="unsafe-content",
            claimant_entity_id="fp:agent:moderator",
            evidence_refs=["evidence://mod/1"],
        )
        server.emit_event(
            event_type="social.revocation",
            session_id=session.session_id,
            producer_entity_id="fp:agent:moderator",
            payload={"target_event_id": post_event.event_id, "dispute_id": dispute.dispute_id},
        )

        server.provenance_record(
            subject_refs=[post_event.event_id],
            policy_refs=["policy:community-v2"],
            outcome="updated",
            signer_ref="fp:agent:moderator",
        )

        audit = server.audit_bundle(session_id=session.session_id)
        self.assertTrue(any(event["event_type"] == "social.revocation" for event in audit["events"]))
        self.assertTrue(any(record["policy_refs"] == ["policy:community-v2"] for record in audit["provenance"]))
        self.assertEqual(len(server.disputes_list()), 1)


if __name__ == "__main__":
    unittest.main()
