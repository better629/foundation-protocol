"""In-memory store implementations for FP runtime."""

from __future__ import annotations

from collections import defaultdict
from threading import RLock

from fp.protocol import (
    Activity,
    Dispute,
    Entity,
    FPEvent,
    Membership,
    Organization,
    ProvenanceRecord,
    Receipt,
    Session,
    Settlement,
)


class InMemoryEntityStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._entities: dict[str, Entity] = {}

    def put(self, entity: Entity) -> None:
        with self._lock:
            self._entities[entity.entity_id] = entity

    def get(self, entity_id: str) -> Entity | None:
        with self._lock:
            return self._entities.get(entity_id)

    def list(self) -> list[Entity]:
        with self._lock:
            return list(self._entities.values())


class InMemoryOrganizationStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._organizations: dict[str, Organization] = {}

    def put(self, organization: Organization) -> None:
        with self._lock:
            self._organizations[organization.organization_id] = organization

    def get(self, organization_id: str) -> Organization | None:
        with self._lock:
            return self._organizations.get(organization_id)

    def list(self) -> list[Organization]:
        with self._lock:
            return list(self._organizations.values())


class InMemoryMembershipStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._memberships: dict[str, Membership] = {}
        self._by_organization: dict[str, set[str]] = defaultdict(set)

    def put(self, membership: Membership) -> None:
        with self._lock:
            self._memberships[membership.membership_id] = membership
            self._by_organization[membership.organization_id].add(membership.membership_id)

    def get(self, membership_id: str) -> Membership | None:
        with self._lock:
            return self._memberships.get(membership_id)

    def by_organization(self, organization_id: str) -> list[Membership]:
        with self._lock:
            return [
                self._memberships[membership_id]
                for membership_id in sorted(self._by_organization.get(organization_id, set()))
                if membership_id in self._memberships
            ]


class InMemorySessionStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._sessions: dict[str, Session] = {}

    def put(self, session: Session) -> None:
        with self._lock:
            self._sessions[session.session_id] = session

    def get(self, session_id: str) -> Session | None:
        with self._lock:
            return self._sessions.get(session_id)

    def list(self) -> list[Session]:
        with self._lock:
            return list(self._sessions.values())


class InMemoryActivityStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._activities: dict[str, Activity] = {}

    def put(self, activity: Activity) -> None:
        with self._lock:
            self._activities[activity.activity_id] = activity

    def get(self, activity_id: str) -> Activity | None:
        with self._lock:
            return self._activities.get(activity_id)

    def list(self, *, session_id: str | None = None) -> list[Activity]:
        with self._lock:
            activities = list(self._activities.values())
            if session_id is None:
                return activities
            return [activity for activity in activities if activity.session_id == session_id]


class InMemoryEventStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._streams: dict[str, list[FPEvent]] = defaultdict(list)

    def append(self, stream_key: str, events: list[FPEvent]) -> None:
        if not events:
            return
        with self._lock:
            self._streams[stream_key].extend(events)

    def replay_from(self, stream_key: str, last_event_id: str | None, *, limit: int) -> list[FPEvent]:
        with self._lock:
            events = self._streams.get(stream_key, [])
            if not events:
                return []

            start_idx = 0
            if last_event_id:
                for idx, event in enumerate(events):
                    if event.event_id == last_event_id:
                        start_idx = idx + 1
                        break
            return events[start_idx : start_idx + limit]


class InMemoryReceiptStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._receipts: dict[str, Receipt] = {}

    def put(self, receipt: Receipt) -> None:
        with self._lock:
            self._receipts[receipt.receipt_id] = receipt

    def get(self, receipt_id: str) -> Receipt | None:
        with self._lock:
            return self._receipts.get(receipt_id)

    def list(self) -> list[Receipt]:
        with self._lock:
            return list(self._receipts.values())


class InMemorySettlementStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._settlements: dict[str, Settlement] = {}

    def put(self, settlement: Settlement) -> None:
        with self._lock:
            self._settlements[settlement.settlement_id] = settlement

    def get(self, settlement_id: str) -> Settlement | None:
        with self._lock:
            return self._settlements.get(settlement_id)

    def list(self) -> list[Settlement]:
        with self._lock:
            return list(self._settlements.values())


class InMemoryDisputeStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._disputes: dict[str, Dispute] = {}

    def put(self, dispute: Dispute) -> None:
        with self._lock:
            self._disputes[dispute.dispute_id] = dispute

    def get(self, dispute_id: str) -> Dispute | None:
        with self._lock:
            return self._disputes.get(dispute_id)

    def list(self) -> list[Dispute]:
        with self._lock:
            return list(self._disputes.values())


class InMemoryProvenanceStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._records: dict[str, ProvenanceRecord] = {}

    def put(self, record: ProvenanceRecord) -> None:
        with self._lock:
            self._records[record.record_id] = record

    def list(self) -> list[ProvenanceRecord]:
        with self._lock:
            return list(self._records.values())


class InMemoryStoreBundle:
    """Convenience aggregate used by FPServer default boot path."""

    def __init__(self) -> None:
        self.entities = InMemoryEntityStore()
        self.organizations = InMemoryOrganizationStore()
        self.memberships = InMemoryMembershipStore()
        self.sessions = InMemorySessionStore()
        self.activities = InMemoryActivityStore()
        self.events = InMemoryEventStore()
        self.receipts = InMemoryReceiptStore()
        self.settlements = InMemorySettlementStore()
        self.disputes = InMemoryDisputeStore()
        self.provenance = InMemoryProvenanceStore()
