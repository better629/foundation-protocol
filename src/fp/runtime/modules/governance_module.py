"""Governance-domain runtime module."""

from __future__ import annotations

from typing import Any, Callable

from fp.policy import PolicyContext, PolicyEngine, PolicyHook
from fp.protocol import FPError, FPErrorCode


class GovernanceModule:
    def __init__(
        self,
        *,
        policy_engine: PolicyEngine,
        provenance_recorder: Callable[..., Any],
    ) -> None:
        self.policy_engine = policy_engine
        self._provenance_recorder = provenance_recorder

    def enforce(
        self,
        *,
        hook: PolicyHook,
        actor_entity_id: str | None,
        session_id: str | None = None,
        activity_id: str | None = None,
        operation: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        context = PolicyContext(
            hook=hook,
            actor_entity_id=actor_entity_id,
            session_id=session_id,
            activity_id=activity_id,
            operation=operation,
            payload=payload or {},
        )
        decision = self.policy_engine.evaluate(context)
        subject_refs = [s for s in [session_id, activity_id, actor_entity_id] if s]
        if not subject_refs and payload:
            for key, value in payload.items():
                if key.endswith("_id") or key.endswith("_ref"):
                    if isinstance(value, str) and value:
                        subject_refs.append(value)
                elif key.endswith("_refs") and isinstance(value, list):
                    subject_refs.extend(str(item) for item in value if item)
        if not subject_refs:
            subject_refs = [f"policy-hook:{hook.value}"]
        self._provenance_recorder(
            subject_refs=subject_refs,
            policy_refs=[decision.policy_ref or "policy:default"],
            outcome="allowed" if decision.allowed else "denied",
            signer_ref="fp:system:policy-engine",
            metadata={"decision_id": decision.decision_id, "reason": decision.reason, "hook": hook.value},
        )
        if not decision.allowed:
            raise FPError(
                FPErrorCode.POLICY_DENIED,
                message=decision.reason,
                details={
                    "decision_id": decision.decision_id,
                    "policy_ref": decision.policy_ref,
                    "hook": hook.value,
                },
            )
