"""Example adapter skeleton implementing FP L0 contract."""

from fp.adapters import AdapterCancelResult, AdapterEvent, AdapterResult, AdapterStartResult
from fp.protocol import ActivityState


class MockAdapter:
    async def start_activity(self, ctx: dict, req: dict) -> AdapterStartResult:
        return AdapterStartResult(
            state=ActivityState.WORKING,
            output={},
            events=[AdapterEvent(event_type="adapter.started", payload={"ctx": ctx})],
        )

    async def cancel_activity(self, ctx: dict, activity_id: str) -> AdapterCancelResult:
        return AdapterCancelResult(canceled=True, reason=f"cancelled:{activity_id}")

    async def poll_updates(self, ctx: dict, activity_id: str) -> list[AdapterEvent]:
        return [AdapterEvent(event_type="adapter.progress", payload={"activity_id": activity_id})]

    async def fetch_result(self, ctx: dict, activity_id: str) -> AdapterResult:
        return AdapterResult(output={"activity_id": activity_id, "status": "done"})
