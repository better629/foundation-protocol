from __future__ import annotations

import unittest

from fp.app import FPClient, FPServer, make_default_entity
from fp.protocol import EntityKind
from fp.transport import FPHTTPPublishedServer


class StorePaginationSemanticsTests(unittest.TestCase):
    def _bootstrap(self) -> tuple[FPServer, FPClient]:
        server = FPServer(server_entity_id="fp:system:pagination")
        server.register_entity(make_default_entity("fp:agent:a", EntityKind.AGENT))
        server.register_entity(make_default_entity("fp:agent:b", EntityKind.AGENT))
        client = FPClient.from_inproc(server)
        return server, client

    def test_session_and_activity_pagination_via_inproc_client(self) -> None:
        _, client = self._bootstrap()

        for i in range(1, 6):
            client.session_create(
                session_id=f"sess-{i:02d}",
                participants={"fp:agent:a", "fp:agent:b"},
                roles={"fp:agent:a": {"coordinator"}, "fp:agent:b": {"worker"}},
            )

        first = client.session_list_page(limit=2)
        second = client.session_list_page(limit=2, cursor=first["next_cursor"])
        third = client.session_list_page(limit=2, cursor=second["next_cursor"])

        self.assertEqual([item["session_id"] for item in first["items"]], ["sess-01", "sess-02"])
        self.assertEqual(first["next_cursor"], "sess-02")
        self.assertEqual([item["session_id"] for item in second["items"]], ["sess-03", "sess-04"])
        self.assertEqual(second["next_cursor"], "sess-04")
        self.assertEqual([item["session_id"] for item in third["items"]], ["sess-05"])
        self.assertIsNone(third["next_cursor"])

        session = client.session_create(
            session_id="sess-activities",
            participants={"fp:agent:a", "fp:agent:b"},
            roles={"fp:agent:a": {"coordinator"}, "fp:agent:b": {"worker"}},
        )
        session_id = session["session_id"]

        for i in range(1, 6):
            client.activity_start(
                activity_id=f"act-{i:02d}",
                session_id=session_id,
                owner_entity_id="fp:agent:b",
                initiator_entity_id="fp:agent:a",
                operation="task.noop",
                input_payload={"i": i},
                auto_execute=False,
            )

        page1 = client.activity_list_page(session_id=session_id, limit=2)
        page2 = client.activity_list_page(session_id=session_id, limit=2, cursor=page1["next_cursor"])
        page3 = client.activity_list_page(session_id=session_id, limit=2, cursor=page2["next_cursor"])

        self.assertEqual([item["activity_id"] for item in page1["items"]], ["act-01", "act-02"])
        self.assertEqual(page1["next_cursor"], "act-02")
        self.assertEqual([item["activity_id"] for item in page2["items"]], ["act-03", "act-04"])
        self.assertEqual(page2["next_cursor"], "act-04")
        self.assertEqual([item["activity_id"] for item in page3["items"]], ["act-05"])
        self.assertIsNone(page3["next_cursor"])

    def test_session_pagination_via_remote_http_client(self) -> None:
        server = FPServer(server_entity_id="fp:system:pagination-remote")
        server.register_entity(make_default_entity("fp:agent:a", EntityKind.AGENT))
        server.register_entity(make_default_entity("fp:agent:b", EntityKind.AGENT))

        with FPHTTPPublishedServer(server, publish_entity_id="fp:agent:b", host="127.0.0.1", port=0) as published:
            client = FPClient.from_http_jsonrpc(published.rpc_url)
            for i in range(1, 4):
                client.session_create(
                    session_id=f"sess-r-{i:02d}",
                    participants={"fp:agent:a", "fp:agent:b"},
                    roles={"fp:agent:a": {"coordinator"}, "fp:agent:b": {"worker"}},
                )

            first = client.session_list_page(limit=2)
            second = client.session_list_page(limit=2, cursor=first["next_cursor"])

            self.assertEqual([item["session_id"] for item in first["items"]], ["sess-r-01", "sess-r-02"])
            self.assertEqual(first["next_cursor"], "sess-r-02")
            self.assertEqual([item["session_id"] for item in second["items"]], ["sess-r-03"])
            self.assertIsNone(second["next_cursor"])


if __name__ == "__main__":
    unittest.main()
