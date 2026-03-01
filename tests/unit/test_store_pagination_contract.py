from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from fp.app import make_default_entity
from fp.protocol import Activity, EntityKind, Membership
from fp.stores.memory import InMemoryStoreBundle
from fp.stores.sqlite import SQLiteStoreBundle


class StorePaginationContractTests(unittest.TestCase):
    def _run_backends(self, fn) -> None:
        memory = InMemoryStoreBundle()
        fn("memory", memory)

        with tempfile.TemporaryDirectory() as tmp:
            sqlite = SQLiteStoreBundle(str(Path(tmp) / "stores.sqlite3"))
            try:
                fn("sqlite", sqlite)
            finally:
                sqlite.close()

    def test_entities_list_page_cursor_contract(self) -> None:
        def _assert_backend(_: str, stores: Any) -> None:
            for i in range(1, 6):
                entity_id = f"fp:agent:{i:02d}"
                stores.entities.put(make_default_entity(entity_id, EntityKind.AGENT))

            first, c1 = stores.entities.list_page(limit=2)
            second, c2 = stores.entities.list_page(limit=2, cursor=c1)
            third, c3 = stores.entities.list_page(limit=2, cursor=c2)

            self.assertEqual([item.entity_id for item in first], ["fp:agent:01", "fp:agent:02"])
            self.assertEqual(c1, "fp:agent:02")
            self.assertEqual([item.entity_id for item in second], ["fp:agent:03", "fp:agent:04"])
            self.assertEqual(c2, "fp:agent:04")
            self.assertEqual([item.entity_id for item in third], ["fp:agent:05"])
            self.assertIsNone(c3)

        self._run_backends(_assert_backend)

    def test_membership_page_scoped_by_organization(self) -> None:
        def _assert_backend(_: str, stores: Any) -> None:
            for idx in range(1, 5):
                stores.memberships.put(
                    Membership(
                        membership_id=f"mem-{idx:02d}",
                        organization_id="org:alpha" if idx <= 3 else "org:beta",
                        member_entity_id=f"fp:agent:{idx:02d}",
                        roles={"member"},
                    )
                )

            first, c1 = stores.memberships.by_organization_page("org:alpha", limit=2)
            second, c2 = stores.memberships.by_organization_page("org:alpha", limit=2, cursor=c1)

            self.assertEqual([item.membership_id for item in first], ["mem-01", "mem-02"])
            self.assertEqual(c1, "mem-02")
            self.assertEqual([item.membership_id for item in second], ["mem-03"])
            self.assertIsNone(c2)

        self._run_backends(_assert_backend)

    def test_activity_page_supports_session_filter(self) -> None:
        def _assert_backend(_: str, stores: Any) -> None:
            stores.activities.put(
                Activity(
                    activity_id="act-01",
                    session_id="sess-a",
                    owner_entity_id="fp:agent:a",
                    initiator_entity_id="fp:agent:b",
                    operation="task.a",
                )
            )
            stores.activities.put(
                Activity(
                    activity_id="act-02",
                    session_id="sess-b",
                    owner_entity_id="fp:agent:a",
                    initiator_entity_id="fp:agent:b",
                    operation="task.b",
                )
            )
            stores.activities.put(
                Activity(
                    activity_id="act-03",
                    session_id="sess-a",
                    owner_entity_id="fp:agent:a",
                    initiator_entity_id="fp:agent:b",
                    operation="task.c",
                )
            )
            stores.activities.put(
                Activity(
                    activity_id="act-04",
                    session_id="sess-a",
                    owner_entity_id="fp:agent:a",
                    initiator_entity_id="fp:agent:b",
                    operation="task.d",
                )
            )

            first, c1 = stores.activities.list_page(session_id="sess-a", limit=2)
            second, c2 = stores.activities.list_page(session_id="sess-a", limit=2, cursor=c1)

            self.assertEqual([item.activity_id for item in first], ["act-01", "act-03"])
            self.assertEqual(c1, "act-03")
            self.assertEqual([item.activity_id for item in second], ["act-04"])
            self.assertIsNone(c2)

        self._run_backends(_assert_backend)

    def test_non_positive_page_limit_rejected(self) -> None:
        def _assert_backend(_: str, stores: Any) -> None:
            with self.assertRaises(ValueError):
                stores.entities.list_page(limit=0)
            with self.assertRaises(ValueError):
                stores.memberships.by_organization_page("org:any", limit=0)
            with self.assertRaises(ValueError):
                stores.activities.list_page(limit=0)

        self._run_backends(_assert_backend)


if __name__ == "__main__":
    unittest.main()
