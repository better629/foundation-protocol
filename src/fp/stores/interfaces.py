"""Storage interfaces for FP runtime state."""

from __future__ import annotations

from typing import Protocol

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


class EntityStore(Protocol):
    def put(self, entity: Entity) -> None: ...

    def get(self, entity_id: str) -> Entity | None: ...

    def list(self) -> list[Entity]: ...


class OrganizationStore(Protocol):
    def put(self, organization: Organization) -> None: ...

    def get(self, organization_id: str) -> Organization | None: ...

    def list(self) -> list[Organization]: ...


class MembershipStore(Protocol):
    def put(self, membership: Membership) -> None: ...

    def get(self, membership_id: str) -> Membership | None: ...

    def by_organization(self, organization_id: str) -> list[Membership]: ...


class SessionStore(Protocol):
    def put(self, session: Session) -> None: ...

    def get(self, session_id: str) -> Session | None: ...

    def list(self) -> list[Session]: ...


class ActivityStore(Protocol):
    def put(self, activity: Activity) -> None: ...

    def get(self, activity_id: str) -> Activity | None: ...

    def list(self, *, session_id: str | None = None) -> list[Activity]: ...


class EventStore(Protocol):
    def append(self, stream_key: str, events: list[FPEvent]) -> None: ...

    def replay_from(
        self,
        stream_key: str,
        last_event_id: str | None,
        *,
        limit: int,
    ) -> list[FPEvent]: ...


class ReceiptStore(Protocol):
    def put(self, receipt: Receipt) -> None: ...

    def get(self, receipt_id: str) -> Receipt | None: ...

    def list(self) -> list[Receipt]: ...


class SettlementStore(Protocol):
    def put(self, settlement: Settlement) -> None: ...

    def get(self, settlement_id: str) -> Settlement | None: ...

    def list(self) -> list[Settlement]: ...


class DisputeStore(Protocol):
    def put(self, dispute: Dispute) -> None: ...

    def get(self, dispute_id: str) -> Dispute | None: ...

    def list(self) -> list[Dispute]: ...


class ProvenanceStore(Protocol):
    def put(self, record: ProvenanceRecord) -> None: ...

    def list(self) -> list[ProvenanceRecord]: ...
