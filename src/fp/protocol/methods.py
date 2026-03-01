"""Typed method parameter/result models for FP operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class InitializeParams:
    supported_versions: list[str]
    entity_id: str
    capabilities: dict[str, Any] = field(default_factory=dict)
    supported_profiles: list[str] = field(default_factory=list)


@dataclass(slots=True)
class InitializeResult:
    negotiated_version: str
    capabilities: dict[str, Any]
    supported_profiles: list[str]


@dataclass(slots=True)
class SessionCreateParams:
    participants: set[str]
    roles: dict[str, set[str]]
    policy_ref: str | None = None
    budget: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ActivityStartParams:
    session_id: str
    owner_entity_id: str
    initiator_entity_id: str
    operation: str
    input_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EventStreamParams:
    session_id: str
    activity_id: str | None = None
    from_event_id: str | None = None
    batch_size: int = 200


@dataclass(slots=True)
class PushConfig:
    push_config_id: str
    url: str
    scope: dict[str, str]
    auth: dict[str, Any] = field(default_factory=dict)
    event_types: list[str] = field(default_factory=list)
