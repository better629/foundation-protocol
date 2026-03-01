"""Composable FP runtime bundle."""

from __future__ import annotations

from dataclasses import dataclass

from fp.economy import DisputeService, MeteringService, ReceiptService, SettlementService
from fp.graph import EntityRegistry, MembershipRegistry, OrganizationRegistry
from fp.observability import CostMeter, CostModel, MetricsRegistry, TokenMeter
from fp.policy import AllowAllPolicyEngine, PolicyEngine
from fp.runtime.activity_engine import ActivityEngine
from fp.runtime.dispatch_engine import DispatchEngine
from fp.runtime.event_engine import EventEngine
from fp.runtime.idempotency import IdempotencyGuard
from fp.runtime.session_engine import SessionEngine
from fp.runtime.modules import ActivityModule, EconomyModule, EventModule, GraphModule, SessionModule
from fp.stores.memory import InMemoryStoreBundle


@dataclass(slots=True)
class RuntimeBundle:
    stores: InMemoryStoreBundle
    policy_engine: PolicyEngine
    graph: GraphModule
    sessions: SessionModule
    activities: ActivityModule
    events: EventModule
    economy: EconomyModule
    idempotency: IdempotencyGuard
    metrics: MetricsRegistry
    token_meter: TokenMeter
    cost_meter: CostMeter


def build_runtime_bundle(
    *,
    stores: InMemoryStoreBundle | None = None,
    policy_engine: PolicyEngine | None = None,
    receipt_secret: str = "fp-local-secret",
) -> RuntimeBundle:
    bundle = stores or InMemoryStoreBundle()
    policy = policy_engine or AllowAllPolicyEngine()

    entity_registry = EntityRegistry(bundle.entities)
    organization_registry = OrganizationRegistry(bundle.entities, bundle.organizations)
    membership_registry = MembershipRegistry(bundle.organizations, bundle.memberships)
    graph = GraphModule(
        entities=entity_registry,
        organizations=organization_registry,
        memberships=membership_registry,
    )

    session_module = SessionModule(SessionEngine(bundle.sessions))
    activity_module = ActivityModule(engine=ActivityEngine(bundle.activities), dispatch=DispatchEngine())
    event_module = EventModule(EventEngine(bundle.events))
    economy_module = EconomyModule(
        metering=MeteringService(),
        receipts=ReceiptService(secret=receipt_secret),
        settlements=SettlementService(),
        disputes=DisputeService(),
    )

    return RuntimeBundle(
        stores=bundle,
        policy_engine=policy,
        graph=graph,
        sessions=session_module,
        activities=activity_module,
        events=event_module,
        economy=economy_module,
        idempotency=IdempotencyGuard(),
        metrics=MetricsRegistry(),
        token_meter=TokenMeter(),
        cost_meter=CostMeter(CostModel(input_per_1k_tokens=0.001, output_per_1k_tokens=0.002)),
    )
