from __future__ import annotations

import asyncio
import unittest

from fp.protocol import ActivityState, FPEvent
from fp.runtime.async_activity_engine import AsyncActivityEngine
from fp.runtime.async_event_engine import AsyncEventEngine
from fp.runtime.async_session_engine import AsyncSessionEngine
from fp.runtime.dispatch_engine import AsyncDispatchEngine, DispatchContext
from fp.stores.memory import InMemoryStoreBundle


class AsyncRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_async_dispatch_engine_executes_concurrent_handlers(self) -> None:
        dispatch = AsyncDispatchEngine()

        async def echo(payload: dict) -> dict:
            await asyncio.sleep(0.01)
            return {"echo": payload["x"]}

        dispatch.register("task.echo", echo)
        ctx = DispatchContext(
            session_id="sess-1",
            activity_id="act-1",
            operation="task.echo",
            actor_entity_id="fp:agent:a",
        )
        outputs = await asyncio.gather(
            *[dispatch.execute(context=ctx, input_payload={"x": idx}) for idx in range(10)]
        )

        self.assertEqual(outputs[0], {"echo": 0})
        self.assertEqual(outputs[-1], {"echo": 9})

    async def test_async_session_activity_and_event_engines_roundtrip(self) -> None:
        stores = InMemoryStoreBundle()
        session_engine = AsyncSessionEngine(stores.sessions)
        activity_engine = AsyncActivityEngine(stores.activities)
        event_engine = AsyncEventEngine(stores.events)

        session = await session_engine.create(
            session_id="sess-1",
            participants={"fp:agent:a", "fp:agent:b"},
            roles={"fp:agent:a": {"coordinator"}, "fp:agent:b": {"worker"}},
        )
        activity = await activity_engine.start(
            activity_id="act-1",
            session_id=session.session_id,
            owner_entity_id="fp:agent:b",
            initiator_entity_id="fp:agent:a",
            operation="task.echo",
            input_payload={"x": 1},
        )
        activity = await activity_engine.transition(activity.activity_id, next_state=ActivityState.WORKING)
        activity = await activity_engine.complete(activity.activity_id, result_payload={"ok": True})

        self.assertEqual(activity.state, ActivityState.COMPLETED)

        await event_engine.publish(
            FPEvent(
                event_id="evt-1",
                event_type="activity.completed",
                session_id=session.session_id,
                activity_id=activity.activity_id,
                producer_entity_id="fp:agent:b",
                payload={"ok": True},
            )
        )
        stream = await event_engine.stream(session_id=session.session_id)
        events = await event_engine.read(stream.stream_id, limit=10)
        await event_engine.ack(stream.stream_id, [event.event_id for event in events])

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "activity.completed")


if __name__ == "__main__":
    unittest.main()
