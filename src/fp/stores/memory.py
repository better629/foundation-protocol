"""In-memory store implementations for FP runtime."""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
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

from .base import InMemoryGroupedKVStore, InMemoryKVStore


class InMemoryEntityStore:
    def __init__(self) -> None:
        self._store = InMemoryKVStore[str, Entity](key_fn=lambda entity: entity.entity_id)

    def put(self, entity: Entity) -> None:
        self._store.put(entity)

    def get(self, entity_id: str) -> Entity | None:
        return self._store.get(entity_id)

    def list(self) -> list[Entity]:
        return self._store.list()

    def list_page(self, *, limit: int = 100, cursor: str | None = None) -> tuple[list[Entity], str | None]:
        return self._store.list_page(limit=limit, cursor=cursor)


class InMemoryOrganizationStore:
    def __init__(self) -> None:
        self._store = InMemoryKVStore[str, Organization](key_fn=lambda organization: organization.organization_id)

    def put(self, organization: Organization) -> None:
        self._store.put(organization)

    def get(self, organization_id: str) -> Organization | None:
        return self._store.get(organization_id)

    def list(self) -> list[Organization]:
        return self._store.list()

    def list_page(self, *, limit: int = 100, cursor: str | None = None) -> tuple[list[Organization], str | None]:
        return self._store.list_page(limit=limit, cursor=cursor)


class InMemoryMembershipStore:
    def __init__(self) -> None:
        self._store = InMemoryGroupedKVStore[str, str, Membership](
            key_fn=lambda membership: membership.membership_id,
            group_fn=lambda membership: membership.organization_id,
        )

    def put(self, membership: Membership) -> None:
        self._store.put(membership)

    def get(self, membership_id: str) -> Membership | None:
        return self._store.get(membership_id)

    def by_organization(self, organization_id: str) -> list[Membership]:
        return self._store.by_group(organization_id)

    def by_organization_page(
        self,
        organization_id: str,
        *,
        limit: int = 100,
        cursor: str | None = None,
    ) -> tuple[list[Membership], str | None]:
        return self._store.by_group_page(organization_id, limit=limit, cursor=cursor)


class InMemorySessionStore:
    def __init__(self) -> None:
        self._store = InMemoryKVStore[str, Session](key_fn=lambda session: session.session_id)

    def put(self, session: Session) -> None:
        self._store.put(session)

    def get(self, session_id: str) -> Session | None:
        return self._store.get(session_id)

    def list(self) -> list[Session]:
        return self._store.list()

    def list_page(self, *, limit: int = 100, cursor: str | None = None) -> tuple[list[Session], str | None]:
        return self._store.list_page(limit=limit, cursor=cursor)


class InMemoryActivityStore:
    def __init__(self) -> None:
        self._store = InMemoryGroupedKVStore[str, str, Activity](
            key_fn=lambda activity: activity.activity_id,
            group_fn=lambda activity: activity.session_id,
        )

    def put(self, activity: Activity) -> None:
        self._store.put(activity)

    def get(self, activity_id: str) -> Activity | None:
        return self._store.get(activity_id)

    def list(self, *, session_id: str | None = None) -> list[Activity]:
        if session_id is None:
            return self._store.list()
        return self._store.by_group(session_id)

    def list_page(
        self,
        *,
        session_id: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> tuple[list[Activity], str | None]:
        if session_id is None:
            return self._store.list_page(limit=limit, cursor=cursor)
        return self._store.by_group_page(session_id, limit=limit, cursor=cursor)


class InMemoryEventStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._streams: dict[str, list[FPEvent]] = defaultdict(list)

    def append(self, stream_key: str, events: list[FPEvent]) -> None:
        if not events:
            return
        with self._lock:
            self._streams[stream_key].extend(deepcopy(events))

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
            return deepcopy(events[start_idx : start_idx + limit])


class InMemoryReceiptStore:
    def __init__(self) -> None:
        self._store = InMemoryKVStore[str, Receipt](key_fn=lambda receipt: receipt.receipt_id)

    def put(self, receipt: Receipt) -> None:
        self._store.put(receipt)

    def get(self, receipt_id: str) -> Receipt | None:
        return self._store.get(receipt_id)

    def list(self) -> list[Receipt]:
        return self._store.list()

    def list_page(self, *, limit: int = 100, cursor: str | None = None) -> tuple[list[Receipt], str | None]:
        return self._store.list_page(limit=limit, cursor=cursor)


class InMemorySettlementStore:
    def __init__(self) -> None:
        self._store = InMemoryKVStore[str, Settlement](key_fn=lambda settlement: settlement.settlement_id)

    def put(self, settlement: Settlement) -> None:
        self._store.put(settlement)

    def get(self, settlement_id: str) -> Settlement | None:
        return self._store.get(settlement_id)

    def list(self) -> list[Settlement]:
        return self._store.list()

    def list_page(self, *, limit: int = 100, cursor: str | None = None) -> tuple[list[Settlement], str | None]:
        return self._store.list_page(limit=limit, cursor=cursor)


class InMemoryDisputeStore:
    def __init__(self) -> None:
        self._store = InMemoryKVStore[str, Dispute](key_fn=lambda dispute: dispute.dispute_id)

    def put(self, dispute: Dispute) -> None:
        self._store.put(dispute)

    def get(self, dispute_id: str) -> Dispute | None:
        return self._store.get(dispute_id)

    def list(self) -> list[Dispute]:
        return self._store.list()

    def list_page(self, *, limit: int = 100, cursor: str | None = None) -> tuple[list[Dispute], str | None]:
        return self._store.list_page(limit=limit, cursor=cursor)


class InMemoryProvenanceStore:
    def __init__(self) -> None:
        self._store = InMemoryKVStore[str, ProvenanceRecord](key_fn=lambda record: record.record_id)

    def put(self, record: ProvenanceRecord) -> None:
        self._store.put(record)

    def list(self) -> list[ProvenanceRecord]:
        return self._store.list()

    def list_page(self, *, limit: int = 100, cursor: str | None = None) -> tuple[list[ProvenanceRecord], str | None]:
        return self._store.list_page(limit=limit, cursor=cursor)


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
