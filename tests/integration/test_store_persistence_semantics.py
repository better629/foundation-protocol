from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fp.app import make_default_entity
from fp.protocol import EntityKind
from fp.stores import RedisStoreBundle, SQLiteStoreBundle


class StorePersistenceSemanticsTests(unittest.TestCase):
    def test_sqlite_bundle_persists_across_instances(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "fp.sqlite3"

            first = SQLiteStoreBundle(str(db_path))
            first.entities.put(make_default_entity("fp:agent:persist", EntityKind.AGENT))
            first.close()

            second = SQLiteStoreBundle(str(db_path))
            loaded = second.entities.get("fp:agent:persist")
            second.close()

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.entity_id, "fp:agent:persist")

    def test_redis_bundle_requires_explicit_stub_opt_in(self) -> None:
        with self.assertRaises(NotImplementedError):
            RedisStoreBundle("redis://localhost:6379/0")

        bundle = RedisStoreBundle("redis://localhost:6379/0", enable_inmemory_stub=True)
        bundle.entities.put(make_default_entity("fp:agent:r", EntityKind.AGENT))
        self.assertIsNotNone(bundle.entities.get("fp:agent:r"))


if __name__ == "__main__":
    unittest.main()
