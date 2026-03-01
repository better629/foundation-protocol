from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from fp.app import make_default_entity
from fp.protocol import EntityKind
from fp.stores.sqlite import SQLiteStoreBundle


class SQLiteJSONCodecTests(unittest.TestCase):
    def test_sqlite_stores_json_text_not_pickle_blob(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "codec.sqlite3"
            store = SQLiteStoreBundle(str(db_path))
            store.entities.put(make_default_entity("fp:agent:codec", EntityKind.AGENT))
            row = store._conn.execute("SELECT value, typeof(value) FROM entities LIMIT 1").fetchone()  # type: ignore[attr-defined]
            store.close()

        self.assertIsNotNone(row)
        value, sql_type = row
        self.assertEqual(sql_type, "text")
        self.assertIsInstance(value, str)
        self.assertTrue(value.startswith("{"))
        self.assertNotIn("\\x80\\x04", value)  # pickle protocol prefix should never appear in JSON text

    def test_roundtrip_entity_preserves_kind_and_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "roundtrip.sqlite3"
            first = SQLiteStoreBundle(str(db_path))
            first.entities.put(make_default_entity("fp:agent:rt", EntityKind.AGENT))
            first.close()

            second = SQLiteStoreBundle(str(db_path))
            loaded = second.entities.get("fp:agent:rt")
            second.close()

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.kind, EntityKind.AGENT)
        self.assertEqual(loaded.identity.version, "v1")


if __name__ == "__main__":
    unittest.main()
