"""SQLite-backed store bundle with persistence semantics."""

from __future__ import annotations

import pickle
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Callable, Generic, TypeVar

from fp.protocol import FPEvent, Membership

K = TypeVar("K")
V = TypeVar("V")


class _SQLiteKVStore(Generic[K, V]):
    def __init__(self, *, conn: sqlite3.Connection, table: str, key_fn: Callable[[V], K]) -> None:
        self._conn = conn
        self._table = table
        self._key_fn = key_fn
        self._lock = RLock()
        with self._conn:
            self._conn.execute(
                f"CREATE TABLE IF NOT EXISTS {self._table} ("
                "key TEXT PRIMARY KEY,"
                "value BLOB NOT NULL"
                ")"
            )

    def put(self, value: V) -> None:
        key = str(self._key_fn(value))
        blob = sqlite3.Binary(pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL))
        with self._lock, self._conn:
            self._conn.execute(
                f"REPLACE INTO {self._table} (key, value) VALUES (?, ?)",
                (key, blob),
            )

    def get(self, key: K) -> V | None:
        with self._lock:
            row = self._conn.execute(
                f"SELECT value FROM {self._table} WHERE key = ?",
                (str(key),),
            ).fetchone()
        if row is None:
            return None
        return pickle.loads(row[0])

    def list(self) -> list[V]:
        with self._lock:
            rows = self._conn.execute(f"SELECT value FROM {self._table} ORDER BY key ASC").fetchall()
        return [pickle.loads(row[0]) for row in rows]


class _SQLiteMembershipStore:
    def __init__(self, *, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._lock = RLock()
        with self._conn:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS memberships ("
                "membership_id TEXT PRIMARY KEY,"
                "organization_id TEXT NOT NULL,"
                "value BLOB NOT NULL"
                ")"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memberships_org_id ON memberships(organization_id)"
            )

    def put(self, membership: Membership) -> None:
        blob = sqlite3.Binary(pickle.dumps(membership, protocol=pickle.HIGHEST_PROTOCOL))
        with self._lock, self._conn:
            self._conn.execute(
                "REPLACE INTO memberships (membership_id, organization_id, value) VALUES (?, ?, ?)",
                (membership.membership_id, membership.organization_id, blob),
            )

    def get(self, membership_id: str) -> Membership | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM memberships WHERE membership_id = ?",
                (membership_id,),
            ).fetchone()
        if row is None:
            return None
        return pickle.loads(row[0])

    def by_organization(self, organization_id: str) -> list[Membership]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT value FROM memberships WHERE organization_id = ? ORDER BY membership_id ASC",
                (organization_id,),
            ).fetchall()
        return [pickle.loads(row[0]) for row in rows]


class _SQLiteEventStore:
    def __init__(self, *, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._lock = RLock()
        with self._conn:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS events ("
                "stream_key TEXT NOT NULL,"
                "seq INTEGER PRIMARY KEY AUTOINCREMENT,"
                "event_id TEXT NOT NULL,"
                "value BLOB NOT NULL"
                ")"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_stream_seq ON events(stream_key, seq)"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_stream_event ON events(stream_key, event_id)"
            )

    def append(self, stream_key: str, events: list[FPEvent]) -> None:
        if not events:
            return
        with self._lock, self._conn:
            self._conn.executemany(
                "INSERT INTO events (stream_key, event_id, value) VALUES (?, ?, ?)",
                [
                    (
                        stream_key,
                        event.event_id,
                        sqlite3.Binary(pickle.dumps(event, protocol=pickle.HIGHEST_PROTOCOL)),
                    )
                    for event in events
                ],
            )

    def replay_from(self, stream_key: str, last_event_id: str | None, *, limit: int) -> list[FPEvent]:
        with self._lock:
            from_seq = 0
            if last_event_id:
                row = self._conn.execute(
                    "SELECT seq FROM events WHERE stream_key = ? AND event_id = ? ORDER BY seq DESC LIMIT 1",
                    (stream_key, last_event_id),
                ).fetchone()
                if row is not None:
                    from_seq = int(row[0])
            rows = self._conn.execute(
                "SELECT value FROM events WHERE stream_key = ? AND seq > ? ORDER BY seq ASC LIMIT ?",
                (stream_key, from_seq, int(limit)),
            ).fetchall()
        return [pickle.loads(row[0]) for row in rows]


class SQLiteStoreBundle:
    """SQLite-backed store bundle with durable semantics."""

    def __init__(self, db_path: str) -> None:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = str(path)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)

        self.entities = _SQLiteKVStore(conn=self._conn, table="entities", key_fn=lambda entity: entity.entity_id)
        self.organizations = _SQLiteKVStore(
            conn=self._conn,
            table="organizations",
            key_fn=lambda organization: organization.organization_id,
        )
        self.memberships = _SQLiteMembershipStore(conn=self._conn)
        self.sessions = _SQLiteKVStore(conn=self._conn, table="sessions", key_fn=lambda session: session.session_id)
        self.activities = _SQLiteKVStore(conn=self._conn, table="activities", key_fn=lambda activity: activity.activity_id)
        self.events = _SQLiteEventStore(conn=self._conn)
        self.receipts = _SQLiteKVStore(conn=self._conn, table="receipts", key_fn=lambda receipt: receipt.receipt_id)
        self.settlements = _SQLiteKVStore(
            conn=self._conn,
            table="settlements",
            key_fn=lambda settlement: settlement.settlement_id,
        )
        self.disputes = _SQLiteKVStore(conn=self._conn, table="disputes", key_fn=lambda dispute: dispute.dispute_id)
        self.provenance = _SQLiteKVStore(conn=self._conn, table="provenance", key_fn=lambda record: record.record_id)

    def close(self) -> None:
        self._conn.close()
