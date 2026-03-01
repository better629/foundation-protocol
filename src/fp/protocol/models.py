"""Core FP domain models used by runtime and API layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .errors import FPError, FPErrorCode


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def isoformat(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _require_non_empty(name: str, value: str) -> str:
    if not value or not value.strip():
        raise FPError(FPErrorCode.INVALID_ARGUMENT, f"{name} must be non-empty")
    return value


class EntityKind(str, Enum):
    AGENT = "agent"
    TOOL = "tool"
    RESOURCE = "resource"
    HUMAN = "human"
    ORGANIZATION = "organization"
    INSTITUTION = "institution"
    SERVICE = "service"
    UI = "ui"


class SessionState(str, Enum):
    CREATED = "created"
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSING = "closing"
    CLOSED = "closed"
    FAILED = "failed"


class ActivityState(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input_required"
    AUTH_REQUIRED = "auth_required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    REJECTED = "rejected"


class MembershipStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class SettlementStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    DISPUTED = "disputed"


class MessageFamily(str, Enum):
    MSG = "FP.MSG"
    SHARE = "FP.SHARE"
    INVOKE = "FP.INVOKE"
    EVENT = "FP.EVENT"
    RECEIPT = "FP.RECEIPT"
    SETTLE = "FP.SETTLE"
    NEGOTIATE = "FP.NEGOTIATE"
    DISPUTE = "FP.DISPUTE"


@dataclass(slots=True)
class Identity:
    method: str
    key_refs: list[str]
    version: str
    issuer: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty("identity.method", self.method)
        _require_non_empty("identity.version", self.version)
        if not self.key_refs:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "identity.key_refs must not be empty")


@dataclass(slots=True)
class CapabilitySummary:
    purpose: list[str]
    risk_tags: list[str] = field(default_factory=list)
    schema_hashes: list[str] = field(default_factory=list)
    price_policy_hints: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.purpose:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "capability_summary.purpose must not be empty")


@dataclass(slots=True)
class PrivacyControl:
    owner: str
    default_visibility: str = "restricted"
    delegation_policy_ref: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty("privacy.owner", self.owner)
        if self.default_visibility not in {"public", "restricted", "private"}:
            raise FPError(
                FPErrorCode.INVALID_ARGUMENT,
                "privacy.default_visibility must be one of public/restricted/private",
            )


@dataclass(slots=True)
class Entity:
    entity_id: str
    kind: EntityKind
    identity: Identity
    capability_summary: CapabilitySummary
    privacy: PrivacyControl
    display_name: str | None = None
    capability_refs: list[str] = field(default_factory=list)
    trust_refs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty("entity.entity_id", self.entity_id)


@dataclass(slots=True)
class OrganizationGovernance:
    policy_refs: list[str]
    role_catalog: list[str]

    def __post_init__(self) -> None:
        if not self.policy_refs:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "governance.policy_refs must not be empty")
        if not self.role_catalog:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "governance.role_catalog must not be empty")


@dataclass(slots=True)
class Organization:
    organization_id: str
    entity: Entity
    governance: OrganizationGovernance
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_non_empty("organization.organization_id", self.organization_id)
        if self.entity.kind is not EntityKind.ORGANIZATION:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "organization.entity.kind must be organization")


@dataclass(slots=True)
class DelegationSpendLimit:
    currency: str
    amount: float

    def __post_init__(self) -> None:
        _require_non_empty("delegation.currency", self.currency)
        if self.amount < 0:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "delegation.amount must be >= 0")


@dataclass(slots=True)
class DelegationConstraints:
    spend_limit: DelegationSpendLimit | None = None
    max_token_limit: int | None = None

    def __post_init__(self) -> None:
        if self.max_token_limit is not None and self.max_token_limit < 0:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "delegation.max_token_limit must be >= 0")


@dataclass(slots=True)
class Delegation:
    scope: list[str]
    constraints: DelegationConstraints = field(default_factory=DelegationConstraints)
    expires_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.scope:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "delegation.scope must not be empty")


@dataclass(slots=True)
class Membership:
    membership_id: str
    organization_id: str
    member_entity_id: str
    roles: set[str]
    status: MembershipStatus = MembershipStatus.ACTIVE
    delegations: list[Delegation] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_non_empty("membership.membership_id", self.membership_id)
        _require_non_empty("membership.organization_id", self.organization_id)
        _require_non_empty("membership.member_entity_id", self.member_entity_id)
        if not self.roles:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "membership.roles must not be empty")


@dataclass(slots=True)
class SessionBudget:
    spend_limit: DelegationSpendLimit | None = None
    token_limit: int | None = None

    def __post_init__(self) -> None:
        if self.token_limit is not None and self.token_limit < 0:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "session.budget.token_limit must be >= 0")


@dataclass(slots=True)
class Session:
    session_id: str
    participants: set[str]
    roles: dict[str, set[str]]
    state: SessionState = SessionState.CREATED
    policy_ref: str | None = None
    budget: SessionBudget = field(default_factory=SessionBudget)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty("session.session_id", self.session_id)
        if len(self.participants) < 1:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "session.participants must not be empty")
        if not self.roles:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "session.roles must not be empty")


@dataclass(slots=True)
class Activity:
    activity_id: str
    session_id: str
    owner_entity_id: str
    initiator_entity_id: str
    state: ActivityState = ActivityState.SUBMITTED
    operation: str | None = None
    input_payload: dict[str, Any] = field(default_factory=dict)
    result_payload: dict[str, Any] | None = None
    result_ref: str | None = None
    status_message: str | None = None
    error: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_non_empty("activity.activity_id", self.activity_id)
        _require_non_empty("activity.session_id", self.session_id)
        _require_non_empty("activity.owner_entity_id", self.owner_entity_id)
        _require_non_empty("activity.initiator_entity_id", self.initiator_entity_id)


@dataclass(slots=True)
class FPEvent:
    event_id: str
    event_type: str
    session_id: str
    producer_entity_id: str
    occurred_at: datetime = field(default_factory=utc_now)
    activity_id: str | None = None
    trace_id: str | None = None
    causation_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    policy_ref: str | None = None
    evidence_refs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require_non_empty("event.event_id", self.event_id)
        _require_non_empty("event.event_type", self.event_type)
        _require_non_empty("event.session_id", self.session_id)
        _require_non_empty("event.producer_entity_id", self.producer_entity_id)


@dataclass(slots=True)
class EventStreamHandle:
    stream_id: str
    session_id: str
    activity_id: str | None = None
    last_read_event_id: str | None = None


@dataclass(slots=True)
class Envelope:
    fp_version: str
    message_id: str
    family: MessageFamily
    trace_id: str
    from_entity: str
    to_entity: str
    payload: dict[str, Any]
    sent_at: datetime = field(default_factory=utc_now)
    span_id: str | None = None
    causation_id: str | None = None
    session_id: str | None = None
    activity_id: str | None = None
    ttl_ms: int | None = None
    extensions: list[str] = field(default_factory=list)
    policy_ref: str | None = None


@dataclass(slots=True)
class MeterRecord:
    meter_id: str
    subject_ref: str
    unit: str
    quantity: float
    metering_policy_ref: str
    metered_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty("meter.meter_id", self.meter_id)
        _require_non_empty("meter.subject_ref", self.subject_ref)
        _require_non_empty("meter.unit", self.unit)
        _require_non_empty("meter.metering_policy_ref", self.metering_policy_ref)
        if self.quantity < 0:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "meter.quantity must be >= 0")


@dataclass(slots=True)
class Receipt:
    receipt_id: str
    activity_id: str
    provider_entity_id: str
    meter_records: list[MeterRecord]
    integrity_proof: str
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_non_empty("receipt.receipt_id", self.receipt_id)
        _require_non_empty("receipt.activity_id", self.activity_id)
        _require_non_empty("receipt.provider_entity_id", self.provider_entity_id)
        _require_non_empty("receipt.integrity_proof", self.integrity_proof)
        if not self.meter_records:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "receipt.meter_records must not be empty")


@dataclass(slots=True)
class Settlement:
    settlement_id: str
    receipt_refs: list[str]
    settlement_ref: str
    status: SettlementStatus = SettlementStatus.PENDING
    amount: float | None = None
    currency: str | None = None
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_non_empty("settlement.settlement_id", self.settlement_id)
        _require_non_empty("settlement.settlement_ref", self.settlement_ref)
        if not self.receipt_refs:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "settlement.receipt_refs must not be empty")
        if self.amount is not None and self.amount < 0:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "settlement.amount must be >= 0")


@dataclass(slots=True)
class Dispute:
    dispute_id: str
    target_ref: str
    reason_code: str
    claimant_entity_id: str
    evidence_refs: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)
    status: str = "open"

    def __post_init__(self) -> None:
        _require_non_empty("dispute.dispute_id", self.dispute_id)
        _require_non_empty("dispute.target_ref", self.target_ref)
        _require_non_empty("dispute.reason_code", self.reason_code)
        _require_non_empty("dispute.claimant_entity_id", self.claimant_entity_id)


@dataclass(slots=True)
class ProvenanceRecord:
    record_id: str
    subject_refs: list[str]
    policy_refs: list[str]
    outcome: str
    signer_ref: str
    timestamp: datetime = field(default_factory=utc_now)
    input_digest_refs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty("provenance.record_id", self.record_id)
        if not self.subject_refs:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "provenance.subject_refs must not be empty")
        if not self.policy_refs:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "provenance.policy_refs must not be empty")
        _require_non_empty("provenance.outcome", self.outcome)
        _require_non_empty("provenance.signer_ref", self.signer_ref)
