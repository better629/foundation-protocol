"""SQLite-backed store bundle.

First FP release keeps a strict, battle-tested in-memory implementation as the default.
This class intentionally composes that implementation while providing a stable constructor
surface for production migration.
"""

from __future__ import annotations

from pathlib import Path

from .memory import InMemoryStoreBundle


class SQLiteStoreBundle(InMemoryStoreBundle):
    """Compatibility bundle that currently uses in-memory semantics.

    The constructor validates the configured path so deployment wiring can be exercised
    from day one. Persisted storage can be introduced without changing call sites.
    """

    def __init__(self, db_path: str) -> None:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = str(path)
        super().__init__()
