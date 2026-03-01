"""Policy decision model."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass(slots=True)
class PolicyDecision:
    allowed: bool
    reason: str
    policy_ref: str | None = None
    details: dict[str, str] = field(default_factory=dict)
    decision_id: str = field(default_factory=lambda: f"dec-{uuid4().hex}")


def allow(reason: str = "allowed", policy_ref: str | None = None) -> PolicyDecision:
    return PolicyDecision(allowed=True, reason=reason, policy_ref=policy_ref)


def deny(reason: str, policy_ref: str | None = None) -> PolicyDecision:
    return PolicyDecision(allowed=False, reason=reason, policy_ref=policy_ref)
