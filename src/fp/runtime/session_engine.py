"""Session lifecycle engine."""

from __future__ import annotations

from fp.protocol import FPError, FPErrorCode, Session, SessionBudget, SessionState, utc_now
from fp.stores.interfaces import SessionStore


class SessionEngine:
    def __init__(self, store: SessionStore) -> None:
        self._store = store

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
        if self._store.get(session_id) is not None:
            raise FPError(FPErrorCode.ALREADY_EXISTS, f"session already exists: {session_id}")
        if len(participants) < 2:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "session requires at least two participants")
        unknown_role_entities = set(roles) - participants
        if unknown_role_entities:
            raise FPError(
                FPErrorCode.INVALID_ARGUMENT,
                message="session roles include entities outside participants",
                details={"unknown_entities": sorted(unknown_role_entities)},
            )
        normalized_roles: dict[str, set[str]] = {}
        for entity_id, role_set in roles.items():
            normalized = set(role_set)
            if not normalized:
                raise FPError(
                    FPErrorCode.INVALID_ARGUMENT,
                    message="session role set must not be empty",
                    details={"entity_id": entity_id},
                )
            normalized_roles[entity_id] = normalized
        for entity_id in participants:
            normalized_roles.setdefault(entity_id, {"participant"})
        session = Session(
            session_id=session_id,
            participants=participants,
            roles=normalized_roles,
            policy_ref=policy_ref,
            budget=budget or SessionBudget(),
            state=SessionState.ACTIVE,
            metadata=metadata or {},
        )
        self._store.put(session)
        return session

    def get(self, session_id: str) -> Session:
        session = self._store.get(session_id)
        if session is None:
            raise FPError(FPErrorCode.NOT_FOUND, f"session not found: {session_id}")
        return session

    def join(self, session_id: str, entity_id: str, roles: set[str] | None = None) -> Session:
        session = self.get(session_id)
        if session.state is not SessionState.ACTIVE:
            raise FPError(
                FPErrorCode.INVALID_STATE_TRANSITION,
                f"cannot join session in state: {session.state.value}",
            )
        session.participants.add(entity_id)
        if roles:
            session.roles[entity_id] = set(roles)
        elif entity_id not in session.roles:
            session.roles[entity_id] = {"participant"}
        session.updated_at = utc_now()
        self._store.put(session)
        return session

    def leave(self, session_id: str, entity_id: str) -> Session:
        session = self.get(session_id)
        if session.state in {SessionState.CLOSED, SessionState.FAILED}:
            raise FPError(
                FPErrorCode.INVALID_STATE_TRANSITION,
                f"cannot leave session in state: {session.state.value}",
            )
        session.participants.discard(entity_id)
        session.roles.pop(entity_id, None)
        session.updated_at = utc_now()
        self._store.put(session)
        return session

    def update(
        self,
        session_id: str,
        *,
        policy_ref: str | None = None,
        budget: SessionBudget | None = None,
        state: SessionState | None = None,
        roles_patch: dict[str, set[str]] | None = None,
    ) -> Session:
        session = self.get(session_id)
        if session.state in {SessionState.CLOSED, SessionState.FAILED}:
            raise FPError(
                FPErrorCode.INVALID_STATE_TRANSITION,
                f"cannot update session in state: {session.state.value}",
            )
        if policy_ref is not None:
            session.policy_ref = policy_ref
        if budget is not None:
            session.budget = budget
        if state is not None:
            session.state = state
        if roles_patch:
            for entity_id, role_set in roles_patch.items():
                session.roles[entity_id] = set(role_set)
                session.participants.add(entity_id)
        session.updated_at = utc_now()
        self._store.put(session)
        return session

    def close(self, session_id: str, reason: str | None = None) -> Session:
        session = self.get(session_id)
        session.state = SessionState.CLOSED
        if reason:
            session.metadata["close_reason"] = reason
        session.updated_at = utc_now()
        self._store.put(session)
        return session

    def list(self) -> list[Session]:
        return self._store.list()
