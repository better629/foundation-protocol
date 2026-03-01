"""Session-domain runtime module."""

from __future__ import annotations

from fp.protocol import Session, SessionBudget, SessionState
from fp.runtime.session_engine import SessionEngine


class SessionModule:
    def __init__(self, engine: SessionEngine) -> None:
        self.engine = engine

    def create(
        self,
        *,
        session_id: str,
        participants: set[str],
        roles: dict[str, set[str]],
        policy_ref: str | None = None,
        budget: SessionBudget | None = None,
        metadata: dict[str, str] | None = None,
    ) -> Session:
        return self.engine.create(
            session_id=session_id,
            participants=participants,
            roles=roles,
            policy_ref=policy_ref,
            budget=budget,
            metadata=metadata,
        )

    def join(self, session_id: str, entity_id: str, roles: set[str] | None = None) -> Session:
        return self.engine.join(session_id, entity_id, roles)

    def update(
        self,
        session_id: str,
        *,
        policy_ref: str | None = None,
        budget: SessionBudget | None = None,
        state: SessionState | None = None,
        roles_patch: dict[str, set[str]] | None = None,
    ) -> Session:
        return self.engine.update(
            session_id,
            policy_ref=policy_ref,
            budget=budget,
            state=state,
            roles_patch=roles_patch,
        )

    def leave(self, session_id: str, entity_id: str) -> Session:
        return self.engine.leave(session_id, entity_id)

    def close(self, session_id: str, reason: str | None = None) -> Session:
        return self.engine.close(session_id, reason)

    def get(self, session_id: str) -> Session:
        return self.engine.get(session_id)

    def list(self) -> list[Session]:
        return self.engine.list()
