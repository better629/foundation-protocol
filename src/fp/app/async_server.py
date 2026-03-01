"""Async facade for FPServer."""

from __future__ import annotations

import asyncio
from typing import Any, Callable

from .server import FPServer


class AsyncFPServer:
    def __init__(self, server: FPServer | None = None, **server_kwargs: Any) -> None:
        self._server = server or FPServer(**server_kwargs)

    @property
    def sync_server(self) -> FPServer:
        return self._server

    @property
    def fp_version(self) -> str:
        return self._server.fp_version

    def register_operation(self, name: str, handler: Callable[[dict[str, Any]], Any]) -> None:
        self._server.register_operation(name, handler)

    def set_token_budget_enforcer(self, enforcer: Callable[[dict[str, Any]], None] | None) -> None:
        self._server.set_token_budget_enforcer(enforcer)

    async def initialize(self, **kwargs: Any) -> dict[str, Any]:
        return await asyncio.to_thread(self._server.initialize, **kwargs)

    async def register_entity(self, entity: Any) -> Any:
        return await asyncio.to_thread(self._server.register_entity, entity)

    async def get_entity(self, entity_id: str) -> Any:
        return await asyncio.to_thread(self._server.get_entity, entity_id)

    async def sessions_create(self, **kwargs: Any) -> Any:
        return await asyncio.to_thread(self._server.sessions_create, **kwargs)

    async def sessions_join(self, **kwargs: Any) -> Any:
        return await asyncio.to_thread(self._server.sessions_join, **kwargs)

    async def sessions_update(self, **kwargs: Any) -> Any:
        return await asyncio.to_thread(self._server.sessions_update, **kwargs)

    async def sessions_get(self, session_id: str) -> Any:
        return await asyncio.to_thread(self._server.sessions_get, session_id)

    async def activities_start(self, **kwargs: Any) -> Any:
        return await asyncio.to_thread(self._server.activities_start, **kwargs)

    async def activities_update(self, **kwargs: Any) -> Any:
        return await asyncio.to_thread(self._server.activities_update, **kwargs)

    async def activities_cancel(self, **kwargs: Any) -> Any:
        return await asyncio.to_thread(self._server.activities_cancel, **kwargs)

    async def activities_result(self, **kwargs: Any) -> Any:
        return await asyncio.to_thread(self._server.activities_result, **kwargs)

    async def events_stream(self, **kwargs: Any) -> Any:
        return await asyncio.to_thread(self._server.events_stream, **kwargs)

    async def events_read(self, **kwargs: Any) -> Any:
        return await asyncio.to_thread(self._server.events_read, **kwargs)

    async def events_ack(self, **kwargs: Any) -> Any:
        return await asyncio.to_thread(self._server.events_ack, **kwargs)
