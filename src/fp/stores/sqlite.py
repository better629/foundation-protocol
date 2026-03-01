"""SQLite-backed store bundle with JSON persistence semantics."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import RLock
from typing import Callable, Generic, TypeVar

from fp.protocol import Activity, FPEvent, Membership

from .codec import (
    decode_activity,
    decode_dispute,
    decode_entity,
    decode_event,
    decode_json,
    decode_membership,
    decode_organization,
    decode_provenance,
    decode_receipt,
    decode_session,
    decode_settlement,
    encode_json,
)

K = TypeVar("K")
V = TypeVar("V")


class _SQLiteKVStore(Generic[K, V]):
    def __init__(
        self,
        *,
        conn: sqlite3.Connection,
        table: str,
        key_fn: Callable[[V], K],
        decoder: Callable[[dict], V],
    ) -> None:
        self._conn = conn
        self._table = table
        self._key_fn = key_fn
        self._decoder = decoder
        self._lock = RLock()
        with self._conn:
            self._conn.execute(
                f"CREATE TABLE IF NOT EXISTS {self._table} ("
                "key TEXT PRIMARY KEY,"
                "value TEXT NOT NULL"
                ")"
            )

    def put(self, value: V) -> None:
        key = str(self._key_fn(value))
        encoded = encode_json(value)
        with self._lock, self._conn:
            self._conn.execute(
                f"REPLACE INTO {self._table} (key, value) VALUES (?, ?)",
                (key, encoded),
            )

    def get(self, key: K) -> V | None:
        with self._lock:
            row = self._conn.execute(
                f"SELECT value FROM {self._table} WHERE key = ?",
                (str(key),),
            ).fetchone()
        if row is None:
            return None
        decoded = decode_json(row[0])
        if not isinstance(decoded, dict):
            raise ValueError(f"invalid JSON payload in table {self._table}")
        return self._decoder(decoded)

    def list(self) -> list[V]:
        with self._lock:
            rows = self._conn.execute(f"SELECT value FROM {self._table} ORDER BY key ASC").fetchall()
        out: list[V] = []
        for row in rows:
            decoded = decode_json(row[0])
            if not isinstance(decoded, dict):
                raise ValueError(f"invalid JSON payload in table {self._table}")
            out.append(self._decoder(decoded))
        return out

    def list_page(self, *, limit: int = 100, cursor: str | None = None) -> tuple[list[V], str | None]:
        if limit <= 0:
            raise ValueError("limit must be > 0")
        where = "WHERE key > ?" if cursor is not None else ""
        params: tuple[object, ...]
        if cursor is not None:
            params = (cursor, int(limit + 1))
        else:
            params = (int(limit + 1),)
        query = f"SELECT key, value FROM {self._table} {where} ORDER BY key ASC LIMIT ?"
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        out: list[V] = []
        for _, raw in rows[:limit]:
            decoded = decode_json(raw)
            if not isinstance(decoded, dict):
                raise ValueError(f"invalid JSON payload in table {self._table}")
            out.append(self._decoder(decoded))
        next_cursor = rows[limit - 1][0] if len(rows) > limit else None
        return out, next_cursor


class _SQLiteMembershipStore:
    def __init__(self, *, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._lock = RLock()
        with self._conn:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS memberships ("
                "membership_id TEXT PRIMARY KEY,"
                "organization_id TEXT NOT NULL,"
                "value TEXT NOT NULL"
                ")"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memberships_org_id ON memberships(organization_id)"
            )

    def put(self, membership: Membership) -> None:
        encoded = encode_json(membership)
        with self._lock, self._conn:
            self._conn.execute(
                "REPLACE INTO memberships (membership_id, organization_id, value) VALUES (?, ?, ?)",
                (membership.membership_id, membership.organization_id, encoded),
            )

    def get(self, membership_id: str) -> Membership | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM memberships WHERE membership_id = ?",
                (membership_id,),
            ).fetchone()
        if row is None:
            return None
        decoded = decode_json(row[0])
        if not isinstance(decoded, dict):
            raise ValueError("invalid membership payload")
        return decode_membership(decoded)

    def by_organization(self, organization_id: str) -> list[Membership]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT value FROM memberships WHERE organization_id = ? ORDER BY membership_id ASC",
                (organization_id,),
            ).fetchall()
        out: list[Membership] = []
        for row in rows:
            decoded = decode_json(row[0])
            if not isinstance(decoded, dict):
                raise ValueError("invalid membership payload")
            out.append(decode_membership(decoded))
        return out

    def by_organization_page(
        self,
        organization_id: str,
        *,
        limit: int = 100,
        cursor: str | None = None,
    ) -> tuple[list[Membership], str | None]:
        if limit <= 0:
            raise ValueError("limit must be > 0")
        if cursor is None:
            query = (
                "SELECT membership_id, value FROM memberships "
                "WHERE organization_id = ? ORDER BY membership_id ASC LIMIT ?"
            )
            params: tuple[object, ...] = (organization_id, int(limit + 1))
        else:
            query = (
                "SELECT membership_id, value FROM memberships "
                "WHERE organization_id = ? AND membership_id > ? "
                "ORDER BY membership_id ASC LIMIT ?"
            )
            params = (organization_id, cursor, int(limit + 1))
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        out: list[Membership] = []
        for _, raw in rows[:limit]:
            decoded = decode_json(raw)
            if not isinstance(decoded, dict):
                raise ValueError("invalid membership payload")
            out.append(decode_membership(decoded))
        next_cursor = rows[limit - 1][0] if len(rows) > limit else None
        return out, next_cursor


class _SQLiteActivityStore:
    def __init__(self, *, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._lock = RLock()
        with self._conn:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS activities ("
                "activity_id TEXT PRIMARY KEY,"
                "session_id TEXT NOT NULL,"
                "value TEXT NOT NULL"
                ")"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_activities_session_activity ON activities(session_id, activity_id)"
            )

    def put(self, activity: Activity) -> None:
        encoded = encode_json(activity)
        with self._lock, self._conn:
            self._conn.execute(
                "REPLACE INTO activities (activity_id, session_id, value) VALUES (?, ?, ?)",
                (activity.activity_id, activity.session_id, encoded),
            )

    def get(self, activity_id: str) -> Activity | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM activities WHERE activity_id = ?",
                (activity_id,),
            ).fetchone()
        if row is None:
            return None
        decoded = decode_json(row[0])
        if not isinstance(decoded, dict):
            raise ValueError("invalid activity payload")
        return decode_activity(decoded)

    def list(self, *, session_id: str | None = None) -> list[Activity]:
        if session_id is None:
            query = "SELECT value FROM activities ORDER BY activity_id ASC"
            params: tuple[object, ...] = ()
        else:
            query = "SELECT value FROM activities WHERE session_id = ? ORDER BY activity_id ASC"
            params = (session_id,)
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        out: list[Activity] = []
        for row in rows:
            decoded = decode_json(row[0])
            if not isinstance(decoded, dict):
                raise ValueError("invalid activity payload")
            out.append(decode_activity(decoded))
        return out

    def list_page(
        self,
        *,
        session_id: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> tuple[list[Activity], str | None]:
        if limit <= 0:
            raise ValueError("limit must be > 0")
        if session_id is None:
            if cursor is None:
                query = "SELECT activity_id, value FROM activities ORDER BY activity_id ASC LIMIT ?"
                params: tuple[object, ...] = (int(limit + 1),)
            else:
                query = (
                    "SELECT activity_id, value FROM activities "
                    "WHERE activity_id > ? ORDER BY activity_id ASC LIMIT ?"
                )
                params = (cursor, int(limit + 1))
        else:
            if cursor is None:
                query = (
                    "SELECT activity_id, value FROM activities "
                    "WHERE session_id = ? ORDER BY activity_id ASC LIMIT ?"
                )
                params = (session_id, int(limit + 1))
            else:
                query = (
                    "SELECT activity_id, value FROM activities "
                    "WHERE session_id = ? AND activity_id > ? "
                    "ORDER BY activity_id ASC LIMIT ?"
                )
                params = (session_id, cursor, int(limit + 1))
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        out: list[Activity] = []
        for _, raw in rows[:limit]:
            decoded = decode_json(raw)
            if not isinstance(decoded, dict):
                raise ValueError("invalid activity payload")
            out.append(decode_activity(decoded))
        next_cursor = rows[limit - 1][0] if len(rows) > limit else None
        return out, next_cursor


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
                "value TEXT NOT NULL"
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
                [(stream_key, event.event_id, encode_json(event)) for event in events],
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

        out: list[FPEvent] = []
        for row in rows:
            decoded = decode_json(row[0])
            if not isinstance(decoded, dict):
                raise ValueError("invalid event payload")
            out.append(decode_event(decoded))
        return out


class SQLiteStoreBundle:
    """SQLite-backed store bundle with durable JSON semantics."""

    def __init__(self, db_path: str) -> None:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = str(path)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)

        self.entities = _SQLiteKVStore(conn=self._conn, table="entities", key_fn=lambda entity: entity.entity_id, decoder=decode_entity)
        self.organizations = _SQLiteKVStore(
            conn=self._conn,
            table="organizations",
            key_fn=lambda organization: organization.organization_id,
            decoder=decode_organization,
        )
        self.memberships = _SQLiteMembershipStore(conn=self._conn)
        self.sessions = _SQLiteKVStore(conn=self._conn, table="sessions", key_fn=lambda session: session.session_id, decoder=decode_session)
        self.activities = _SQLiteActivityStore(conn=self._conn)
        self.events = _SQLiteEventStore(conn=self._conn)
        self.receipts = _SQLiteKVStore(conn=self._conn, table="receipts", key_fn=lambda receipt: receipt.receipt_id, decoder=decode_receipt)
        self.settlements = _SQLiteKVStore(
            conn=self._conn,
            table="settlements",
            key_fn=lambda settlement: settlement.settlement_id,
            decoder=decode_settlement,
        )
        self.disputes = _SQLiteKVStore(conn=self._conn, table="disputes", key_fn=lambda dispute: dispute.dispute_id, decoder=decode_dispute)
        self.provenance = _SQLiteKVStore(conn=self._conn, table="provenance", key_fn=lambda record: record.record_id, decoder=decode_provenance)

    def close(self) -> None:
        self._conn.close()
