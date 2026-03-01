"""Redis-backed store bundle (explicit opt-in stub)."""

from __future__ import annotations

from .memory import InMemoryStoreBundle


class RedisStoreBundle:
    """Placeholder Redis bundle that forbids silent in-memory fallback by default."""

    def __init__(self, redis_url: str, *, enable_inmemory_stub: bool = False) -> None:
        if not redis_url:
            raise ValueError("redis_url must be non-empty")
        self.redis_url = redis_url
        if not enable_inmemory_stub:
            raise NotImplementedError(
                "Redis backend is not bundled yet. "
                "Pass enable_inmemory_stub=True for explicit local-only behavior."
            )

        delegate = InMemoryStoreBundle()
        self.entities = delegate.entities
        self.organizations = delegate.organizations
        self.memberships = delegate.memberships
        self.sessions = delegate.sessions
        self.activities = delegate.activities
        self.events = delegate.events
        self.receipts = delegate.receipts
        self.settlements = delegate.settlements
        self.disputes = delegate.disputes
        self.provenance = delegate.provenance
