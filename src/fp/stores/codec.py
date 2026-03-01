"""JSON codec for FP store persistence."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from fp.protocol import (
    Activity,
    ActivityState,
    CapabilitySummary,
    Delegation,
    DelegationConstraints,
    DelegationSpendLimit,
    Dispute,
    Entity,
    EntityKind,
    FPEvent,
    Identity,
    Membership,
    MembershipStatus,
    Organization,
    OrganizationGovernance,
    PrivacyControl,
    ProvenanceRecord,
    Receipt,
    Session,
    SessionBudget,
    SessionState,
    Settlement,
    SettlementStatus,
    MeterRecord,
)


def encode_json(value: Any) -> str:
    return json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def decode_json(raw: str) -> Any:
    return json.loads(raw)


def decode_entity(data: dict[str, Any]) -> Entity:
    return Entity(
        entity_id=str(data["entity_id"]),
        kind=EntityKind(str(data["kind"])),
        display_name=data.get("display_name"),
        identity=Identity(
            method=str(data.get("identity", {}).get("method", "did:example")),
            key_refs=list(data.get("identity", {}).get("key_refs", [])),
            version=str(data.get("identity", {}).get("version", "v1")),
            issuer=data.get("identity", {}).get("issuer"),
        ),
        capability_summary=CapabilitySummary(
            purpose=list(data.get("capability_summary", {}).get("purpose", [])),
            risk_tags=list(data.get("capability_summary", {}).get("risk_tags", [])),
            schema_hashes=list(data.get("capability_summary", {}).get("schema_hashes", [])),
            price_policy_hints=list(data.get("capability_summary", {}).get("price_policy_hints", [])),
        ),
        privacy=PrivacyControl(
            owner=str(data.get("privacy", {}).get("owner", data["entity_id"])),
            default_visibility=str(data.get("privacy", {}).get("default_visibility", "restricted")),
            delegation_policy_ref=data.get("privacy", {}).get("delegation_policy_ref"),
        ),
        capability_refs=list(data.get("capability_refs", [])),
        trust_refs=list(data.get("trust_refs", [])),
        metadata=dict(data.get("metadata", {})),
    )


def decode_organization(data: dict[str, Any]) -> Organization:
    return Organization(
        organization_id=str(data["organization_id"]),
        entity=decode_entity(dict(data.get("entity", {}))),
        governance=OrganizationGovernance(
            policy_refs=list(data.get("governance", {}).get("policy_refs", [])),
            role_catalog=list(data.get("governance", {}).get("role_catalog", [])),
        ),
        created_at=_dt(data.get("created_at")),
    )


def decode_membership(data: dict[str, Any]) -> Membership:
    return Membership(
        membership_id=str(data["membership_id"]),
        organization_id=str(data["organization_id"]),
        member_entity_id=str(data["member_entity_id"]),
        roles=set(data.get("roles", [])),
        status=MembershipStatus(str(data.get("status", MembershipStatus.ACTIVE.value))),
        delegations=[decode_delegation(item) for item in data.get("delegations", [])],
        created_at=_dt(data.get("created_at")),
        updated_at=_dt(data.get("updated_at")),
    )


def decode_session(data: dict[str, Any]) -> Session:
    return Session(
        session_id=str(data["session_id"]),
        participants=set(data.get("participants", [])),
        roles={str(entity_id): set(role_values) for entity_id, role_values in dict(data.get("roles", {})).items()},
        state=SessionState(str(data.get("state", SessionState.CREATED.value))),
        policy_ref=data.get("policy_ref"),
        budget=decode_session_budget(dict(data.get("budget", {}))),
        created_at=_dt(data.get("created_at")),
        updated_at=_dt(data.get("updated_at")),
        metadata=dict(data.get("metadata", {})),
    )


def decode_activity(data: dict[str, Any]) -> Activity:
    state = ActivityState(str(data.get("state", ActivityState.SUBMITTED.value)))
    return Activity(
        activity_id=str(data["activity_id"]),
        session_id=str(data["session_id"]),
        owner_entity_id=str(data["owner_entity_id"]),
        initiator_entity_id=str(data["initiator_entity_id"]),
        state=state,
        operation=data.get("operation"),
        input_payload=dict(data.get("input_payload", {})),
        result_payload=dict(data["result_payload"]) if isinstance(data.get("result_payload"), dict) else data.get("result_payload"),
        result_ref=data.get("result_ref"),
        status_message=data.get("status_message"),
        error=dict(data["error"]) if isinstance(data.get("error"), dict) else data.get("error"),
        created_at=_dt(data.get("created_at")),
        updated_at=_dt(data.get("updated_at")),
    )


def decode_event(data: dict[str, Any]) -> FPEvent:
    return FPEvent(
        event_id=str(data["event_id"]),
        event_type=str(data["event_type"]),
        session_id=str(data["session_id"]),
        producer_entity_id=str(data["producer_entity_id"]),
        occurred_at=_dt(data.get("occurred_at")),
        activity_id=data.get("activity_id"),
        trace_id=data.get("trace_id"),
        causation_id=data.get("causation_id"),
        payload=dict(data.get("payload", {})),
        policy_ref=data.get("policy_ref"),
        evidence_refs=list(data.get("evidence_refs", [])),
    )


def decode_receipt(data: dict[str, Any]) -> Receipt:
    return Receipt(
        receipt_id=str(data["receipt_id"]),
        activity_id=str(data["activity_id"]),
        provider_entity_id=str(data["provider_entity_id"]),
        meter_records=[decode_meter_record(item) for item in data.get("meter_records", [])],
        integrity_proof=str(data.get("integrity_proof", "")),
        created_at=_dt(data.get("created_at")),
    )


def decode_settlement(data: dict[str, Any]) -> Settlement:
    return Settlement(
        settlement_id=str(data["settlement_id"]),
        receipt_refs=list(data.get("receipt_refs", [])),
        settlement_ref=str(data["settlement_ref"]),
        status=SettlementStatus(str(data.get("status", SettlementStatus.PENDING.value))),
        amount=data.get("amount"),
        currency=data.get("currency"),
        created_at=_dt(data.get("created_at")),
    )


def decode_dispute(data: dict[str, Any]) -> Dispute:
    return Dispute(
        dispute_id=str(data["dispute_id"]),
        target_ref=str(data["target_ref"]),
        reason_code=str(data["reason_code"]),
        claimant_entity_id=str(data["claimant_entity_id"]),
        evidence_refs=list(data.get("evidence_refs", [])),
        created_at=_dt(data.get("created_at")),
        status=str(data.get("status", "open")),
    )


def decode_provenance(data: dict[str, Any]) -> ProvenanceRecord:
    return ProvenanceRecord(
        record_id=str(data["record_id"]),
        subject_refs=list(data.get("subject_refs", [])),
        policy_refs=list(data.get("policy_refs", [])),
        outcome=str(data["outcome"]),
        signer_ref=str(data["signer_ref"]),
        timestamp=_dt(data.get("timestamp")),
        input_digest_refs=list(data.get("input_digest_refs", [])),
        metadata=dict(data.get("metadata", {})),
    )


def decode_meter_record(data: dict[str, Any]) -> MeterRecord:
    return MeterRecord(
        meter_id=str(data["meter_id"]),
        subject_ref=str(data["subject_ref"]),
        unit=str(data["unit"]),
        quantity=float(data["quantity"]),
        metering_policy_ref=str(data["metering_policy_ref"]),
        metered_at=_dt(data.get("metered_at")),
        metadata=dict(data.get("metadata", {})),
    )


def decode_session_budget(data: dict[str, Any]) -> SessionBudget:
    spend = data.get("spend_limit")
    spend_limit = None
    if isinstance(spend, dict):
        spend_limit = DelegationSpendLimit(currency=str(spend["currency"]), amount=float(spend["amount"]))
    return SessionBudget(spend_limit=spend_limit, token_limit=data.get("token_limit"))


def decode_delegation(data: dict[str, Any]) -> Delegation:
    constraints_raw = dict(data.get("constraints", {}))
    spend_raw = constraints_raw.get("spend_limit")
    spend_limit = None
    if isinstance(spend_raw, dict):
        spend_limit = DelegationSpendLimit(currency=str(spend_raw["currency"]), amount=float(spend_raw["amount"]))
    constraints = DelegationConstraints(
        spend_limit=spend_limit,
        max_token_limit=constraints_raw.get("max_token_limit"),
    )
    return Delegation(
        scope=list(data.get("scope", [])),
        constraints=constraints,
        expires_at=_dt_or_none(data.get("expires_at")),
    )


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, set):
        return sorted(_jsonable(item) for item in value)
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    if isinstance(value, str) and value:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    return datetime.now(timezone.utc)


def _dt_or_none(value: Any) -> datetime | None:
    if value is None:
        return None
    return _dt(value)


__all__ = [
    "decode_activity",
    "decode_dispute",
    "decode_entity",
    "decode_event",
    "decode_json",
    "decode_membership",
    "decode_organization",
    "decode_provenance",
    "decode_receipt",
    "decode_session",
    "decode_settlement",
    "encode_json",
]
