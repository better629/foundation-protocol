from __future__ import annotations

import asyncio
import unittest

from fp.app import AsyncFPClient, AsyncFPServer, make_default_entity
from fp.protocol import EntityKind
from fp.transport import FPHTTPPublishedServer


class AsyncEndToEndTests(unittest.IsolatedAsyncioTestCase):
    async def test_async_client_inproc_concurrent_activities(self) -> None:
        server = AsyncFPServer(server_entity_id="fp:system:async")
        await server.register_entity(make_default_entity("fp:agent:a", EntityKind.AGENT))
        await server.register_entity(make_default_entity("fp:agent:b", EntityKind.AGENT))

        async def quote(payload: dict) -> dict:
            await asyncio.sleep(0.01)
            return {"price": payload["price"], "quoted": True}

        server.register_operation("task.quote", quote)
        client = AsyncFPClient.from_inproc(server)

        session = await client.session_create(
            participants={"fp:agent:a", "fp:agent:b"},
            roles={"fp:agent:a": {"buyer"}, "fp:agent:b": {"seller"}},
        )
        session_id = session["session_id"]

        activities = await asyncio.gather(
            *[
                client.activity_start(
                    session_id=session_id,
                    owner_entity_id="fp:agent:b",
                    initiator_entity_id="fp:agent:a",
                    operation="task.quote",
                    input_payload={"price": idx},
                )
                for idx in range(12)
            ]
        )

        self.assertTrue(all(activity["state"] == "completed" for activity in activities))
        self.assertEqual({activity["result_payload"]["price"] for activity in activities}, set(range(12)))

    async def test_async_http_client_reaches_published_server(self) -> None:
        server = AsyncFPServer(server_entity_id="fp:system:async-http")
        await server.register_entity(make_default_entity("fp:agent:a", EntityKind.AGENT))
        await server.register_entity(make_default_entity("fp:agent:b", EntityKind.AGENT))
        server.register_operation("task.echo", lambda payload: {"echo": payload["value"]})

        with FPHTTPPublishedServer(server.sync_server, publish_entity_id="fp:agent:b", host="127.0.0.1", port=0) as published:
            client = AsyncFPClient.from_http_jsonrpc(published.rpc_url)
            ping = await client.ping()
            self.assertEqual(ping["ok"], True)

            session = await client.session_create(
                participants={"fp:agent:a", "fp:agent:b"},
                roles={"fp:agent:a": {"caller"}, "fp:agent:b": {"callee"}},
            )
            activity = await client.activity_start(
                session_id=session["session_id"],
                owner_entity_id="fp:agent:b",
                initiator_entity_id="fp:agent:a",
                operation="task.echo",
                input_payload={"value": "ok"},
            )
            self.assertEqual(activity["state"], "completed")
            self.assertEqual(activity["result_payload"]["echo"], "ok")


if __name__ == "__main__":
    unittest.main()
