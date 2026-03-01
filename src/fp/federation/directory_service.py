"""In-memory FP directory service with TTL, ACL, and health semantics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Callable

from fp.protocol import FPError, FPErrorCode

from .card_signing import ensure_not_expired, verify_server_card
from .network import FPServerCard


@dataclass(slots=True)
class DirectoryEntry:
    card: FPServerCard
    healthy: bool = True
    health_reason: str | None = None
    last_heartbeat_at: str | None = None


class DirectoryService:
    def __init__(
        self,
        *,
        public_keys: dict[str, str] | None = None,
        require_signature: bool = False,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self._lock = RLock()
        self._entries: dict[str, DirectoryEntry] = {}
        self._public_keys = dict(public_keys or {})
        self._require_signature = require_signature
        self._now_fn = now_fn or (lambda: datetime.now(tz=timezone.utc))

    def publish(self, card: FPServerCard, *, actor_ref: str | None = None, upsert: bool = True) -> FPServerCard:
        self._authorize_publish(card, actor_ref=actor_ref)
        self._verify_signature(card)
        ensure_not_expired(card, now=self._now())
        with self._lock:
            exists = card.entity_id in self._entries
            if exists and not upsert:
                raise FPError(FPErrorCode.ALREADY_EXISTS, f"server card already exists: {card.entity_id}")
            self._entries[card.entity_id] = DirectoryEntry(card=FPServerCard.from_dict(card.to_dict()))
        return FPServerCard.from_dict(card.to_dict())

    def resolve(
        self,
        entity_id: str,
        *,
        actor_ref: str | None = None,
        require_healthy: bool = False,
    ) -> FPServerCard:
        entry = self._get_valid_entry(entity_id)
        self._authorize_read(entry.card, actor_ref=actor_ref)
        if require_healthy and not entry.healthy:
            raise FPError(
                FPErrorCode.NOT_FOUND,
                message="server card is currently unhealthy",
                details={"entity_id": entity_id, "reason": entry.health_reason},
            )
        return FPServerCard.from_dict(entry.card.to_dict())

    def list(self, *, actor_ref: str | None = None, require_healthy: bool = False) -> list[FPServerCard]:
        with self._lock:
            entity_ids = list(self._entries.keys())
        out: list[FPServerCard] = []
        for entity_id in entity_ids:
            try:
                out.append(self.resolve(entity_id, actor_ref=actor_ref, require_healthy=require_healthy))
            except FPError:
                continue
        return out

    def heartbeat(
        self,
        entity_id: str,
        *,
        actor_ref: str | None = None,
        replacement_card: FPServerCard | None = None,
    ) -> FPServerCard:
        if replacement_card is not None:
            if replacement_card.entity_id != entity_id:
                raise FPError(FPErrorCode.INVALID_ARGUMENT, "replacement card entity mismatch")
            card = self.publish(replacement_card, actor_ref=actor_ref, upsert=True)
            with self._lock:
                entry = self._entries[entity_id]
                entry.last_heartbeat_at = _iso(self._now())
            return card

        with self._lock:
            entry = self._entries.get(entity_id)
            if entry is None:
                raise FPError(FPErrorCode.NOT_FOUND, f"server card not found: {entity_id}")
            card = entry.card
        self._authorize_publish(card, actor_ref=actor_ref)

        if card.sign_alg not in {None, "none"}:
            raise FPError(
                FPErrorCode.INVALID_ARGUMENT,
                "signed cards require replacement_card on heartbeat refresh",
            )

        ttl = card.ttl_seconds or 600
        now_ts = self._now()
        updated = FPServerCard.from_dict(
            {
                **card.to_dict(),
                "issued_at": _iso(now_ts),
                "expires_at": _iso(now_ts + timedelta(seconds=ttl)),
            }
        )
        with self._lock:
            entry = self._entries[entity_id]
            entry.card = updated
            entry.last_heartbeat_at = _iso(now_ts)
        return FPServerCard.from_dict(updated.to_dict())

    def set_health(self, entity_id: str, *, healthy: bool, reason: str | None = None) -> None:
        with self._lock:
            entry = self._entries.get(entity_id)
            if entry is None:
                raise FPError(FPErrorCode.NOT_FOUND, f"server card not found: {entity_id}")
            entry.healthy = healthy
            entry.health_reason = reason

    def health(self, entity_id: str) -> dict[str, str | bool | None]:
        with self._lock:
            entry = self._entries.get(entity_id)
            if entry is None:
                raise FPError(FPErrorCode.NOT_FOUND, f"server card not found: {entity_id}")
            return {
                "entity_id": entity_id,
                "healthy": entry.healthy,
                "reason": entry.health_reason,
                "last_heartbeat_at": entry.last_heartbeat_at,
            }

    def _get_valid_entry(self, entity_id: str) -> DirectoryEntry:
        with self._lock:
            entry = self._entries.get(entity_id)
        if entry is None:
            raise FPError(FPErrorCode.NOT_FOUND, f"server card not found: {entity_id}")
        try:
            ensure_not_expired(entry.card, now=self._now())
        except FPError:
            with self._lock:
                self._entries.pop(entity_id, None)
            raise
        return entry

    def _verify_signature(self, card: FPServerCard) -> None:
        if card.sign_alg in {None, "none"}:
            if self._require_signature:
                raise FPError(FPErrorCode.AUTH_REQUIRED, "directory requires signed server cards")
            return
        if not verify_server_card(card, public_keys=self._public_keys):
            raise FPError(FPErrorCode.AUTH_REQUIRED, "invalid server card signature")

    def _authorize_publish(self, card: FPServerCard, *, actor_ref: str | None) -> None:
        acl_publish = _acl_values(card.metadata.get("acl_publish"))
        if not acl_publish:
            return
        if actor_ref is None or actor_ref not in acl_publish:
            raise FPError(FPErrorCode.AUTHZ_DENIED, "publish denied by directory ACL")

    def _authorize_read(self, card: FPServerCard, *, actor_ref: str | None) -> None:
        acl_read = _acl_values(card.metadata.get("acl_read"))
        if not acl_read:
            return
        if actor_ref is None or actor_ref not in acl_read:
            raise FPError(FPErrorCode.AUTHZ_DENIED, "read denied by directory ACL")

    def _now(self) -> datetime:
        return self._now_fn().astimezone(timezone.utc)


def _acl_values(value: object) -> set[str]:
    if isinstance(value, list):
        return {str(item) for item in value}
    if isinstance(value, set):
        return {str(item) for item in value}
    if isinstance(value, tuple):
        return {str(item) for item in value}
    return set()


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = ["DirectoryEntry", "DirectoryService"]
