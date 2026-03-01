from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fp.protocol import Activity
from fp.stores.memory import InMemoryActivityStore
from fp.stores.sqlite import SQLiteStoreBundle


class ActivityStoreSessionIndexTests(unittest.TestCase):
    def test_memory_store_uses_group_index_for_session_paging(self) -> None:
        store = InMemoryActivityStore()
        for i in range(1, 6):
            store.put(
                Activity(
                    activity_id=f"act-{i:02d}",
                    session_id="sess-a" if i % 2 else "sess-b",
                    owner_entity_id="fp:agent:a",
                    initiator_entity_id="fp:agent:b",
                    operation="task.noop",
                )
            )

        with patch.object(store._store, "by_group_page", wraps=store._store.by_group_page) as grouped_page:  # type: ignore[attr-defined]
            with patch.object(store._store, "list_page", wraps=store._store.list_page) as list_page:  # type: ignore[attr-defined]
                page, _ = store.list_page(session_id="sess-a", limit=2)

        self.assertEqual(len(page), 2)
        grouped_page.assert_called_once()
        list_page.assert_not_called()

    def test_sqlite_store_has_session_activity_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = SQLiteStoreBundle(str(Path(tmp) / "fp.sqlite3"))
            try:
                indexes = bundle._conn.execute("PRAGMA index_list('activities')").fetchall()  # type: ignore[attr-defined]
            finally:
                bundle.close()

        index_names = {row[1] for row in indexes}
        self.assertIn("idx_activities_session_activity", index_names)


if __name__ == "__main__":
    unittest.main()
