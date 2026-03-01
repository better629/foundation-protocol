"""Redis-backed store bundle.

First FP release keeps a strict, battle-tested in-memory implementation as the default.
This class exposes a stable constructor for runtime integration tests and deployment wiring.
"""

from __future__ import annotations

from .memory import InMemoryStoreBundle


class RedisStoreBundle(InMemoryStoreBundle):
    """Compatibility bundle that currently uses in-memory semantics."""

    def __init__(self, redis_url: str) -> None:
        if not redis_url:
            raise ValueError("redis_url must be non-empty")
        self.redis_url = redis_url
        super().__init__()
