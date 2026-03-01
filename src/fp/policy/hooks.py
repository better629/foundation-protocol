"""Policy hook interfaces used by runtime boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from .decision import PolicyDecision, allow


class PolicyHook(str, Enum):
    PRE_INVOKE = "PRE_INVOKE"
    PRE_ROLE_CHANGE = "PRE_ROLE_CHANGE"
    PRE_SETTLE = "PRE_SETTLE"
    POST_EVENT_AUDIT = "POST_EVENT_AUDIT"


@dataclass(slots=True)
class PolicyContext:
    hook: PolicyHook
    actor_entity_id: str | None = None
    session_id: str | None = None
    activity_id: str | None = None
    operation: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


class PolicyEngine(Protocol):
    def evaluate(self, context: PolicyContext) -> PolicyDecision: ...


class AllowAllPolicyEngine:
    def evaluate(self, context: PolicyContext) -> PolicyDecision:
        return allow(reason=f"default-allow:{context.hook.value.lower()}")
