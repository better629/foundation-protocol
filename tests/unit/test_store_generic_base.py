from __future__ import annotations

import unittest

from fp.app import make_default_entity
from fp.protocol import EntityKind, Membership
from fp.stores.base import InMemoryGroupedKVStore, InMemoryKVStore


class StoreGenericBaseTests(unittest.TestCase):
    def test_inmemory_kv_store_copies_values(self) -> None:
        store = InMemoryKVStore[str, object](key_fn=lambda item: getattr(item, "entity_id"))
        entity = make_default_entity("fp:agent:store-a", EntityKind.AGENT)
        store.put(entity)
        entity.display_name = "mutated-outside"

        loaded = store.get("fp:agent:store-a")
        self.assertIsNotNone(loaded)
        self.assertNotEqual(loaded.display_name, "mutated-outside")

    def test_inmemory_grouped_store_indexes_by_group(self) -> None:
        store = InMemoryGroupedKVStore[str, str, Membership](
            key_fn=lambda membership: membership.membership_id,
            group_fn=lambda membership: membership.organization_id,
        )
        m1 = Membership(
            membership_id="mem-1",
            organization_id="org-1",
            member_entity_id="fp:agent:a",
            roles={"member"},
        )
        m2 = Membership(
            membership_id="mem-2",
            organization_id="org-1",
            member_entity_id="fp:agent:b",
            roles={"member"},
        )
        m3 = Membership(
            membership_id="mem-3",
            organization_id="org-2",
            member_entity_id="fp:agent:c",
            roles={"member"},
        )
        store.put(m1)
        store.put(m2)
        store.put(m3)

        org1 = store.by_group("org-1")
        org2 = store.by_group("org-2")
        self.assertEqual([membership.membership_id for membership in org1], ["mem-1", "mem-2"])
        self.assertEqual([membership.membership_id for membership in org2], ["mem-3"])


if __name__ == "__main__":
    unittest.main()
