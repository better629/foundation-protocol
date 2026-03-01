"""Async FP client API."""

from __future__ import annotations

import asyncio
import ssl
from typing import Any

from fp.app.client import FPClient
from fp.transport.client_http_jsonrpc import HTTPJSONRPCClientTransport
from fp.transport.client_inproc import InProcessJSONRPCClientTransport

from .async_server import AsyncFPServer


class AsyncFPClient:
    def __init__(self, client: FPClient) -> None:
        self._client = client

    @classmethod
    def from_inproc(cls, server: AsyncFPServer | Any) -> "AsyncFPClient":
        if isinstance(server, AsyncFPServer):
            transport = InProcessJSONRPCClientTransport(server.sync_server)
            return cls(FPClient(server=None, transport=transport))
        transport = InProcessJSONRPCClientTransport(server)
        return cls(FPClient(server=None, transport=transport))

    @classmethod
    def from_http_jsonrpc(
        cls,
        rpc_url: str,
        *,
        timeout_seconds: float = 10.0,
        headers: dict[str, str] | None = None,
        ssl_context: ssl.SSLContext | None = None,
    ) -> "AsyncFPClient":
        transport = HTTPJSONRPCClientTransport(
            rpc_url,
            timeout_seconds=timeout_seconds,
            headers=headers,
            ssl_context=ssl_context,
        )
        return cls(FPClient(server=None, transport=transport))

    async def initialize(self, *, supported_versions: list[str], entity_id: str, profile: str | None = None) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._client.initialize,
            supported_versions=supported_versions,
            entity_id=entity_id,
            profile=profile,
        )

    async def ping(self) -> dict[str, Any]:
        return await asyncio.to_thread(self._client.ping)

    async def register_entity(self, entity: Any) -> Any:
        return await asyncio.to_thread(self._client.register_entity, entity)

    async def get_entity(self, entity_id: str) -> Any:
        return await asyncio.to_thread(self._client.get_entity, entity_id)

    async def session_create(
        self,
        *,
        participants: set[str],
        roles: dict[str, set[str]],
        policy_ref: str | None = None,
        budget: Any | None = None,
    ) -> Any:
        return await asyncio.to_thread(
            self._client.session_create,
            participants=participants,
            roles=roles,
            policy_ref=policy_ref,
            budget=budget,
        )

    async def session_get(self, session_id: str) -> Any:
        return await asyncio.to_thread(self._client.session_get, session_id)

    async def activity_start(
        self,
        *,
        session_id: str,
        owner_entity_id: str,
        initiator_entity_id: str,
        operation: str,
        input_payload: dict[str, Any],
        auto_execute: bool = True,
    ) -> Any:
        return await asyncio.to_thread(
            self._client.activity_start,
            session_id=session_id,
            owner_entity_id=owner_entity_id,
            initiator_entity_id=initiator_entity_id,
            operation=operation,
            input_payload=input_payload,
            auto_execute=auto_execute,
        )

    async def activity_result(self, *, activity_id: str) -> Any:
        return await asyncio.to_thread(self._client.activity_result, activity_id=activity_id)

    async def activity_update(
        self,
        *,
        activity_id: str,
        state: Any,
        status_message: str | None = None,
        patch: dict[str, Any] | None = None,
    ) -> Any:
        return await asyncio.to_thread(
            self._client.activity_update,
            activity_id=activity_id,
            state=state,
            status_message=status_message,
            patch=patch,
        )

    async def activity_cancel(self, *, activity_id: str, reason: str | None = None) -> Any:
        return await asyncio.to_thread(self._client.activity_cancel, activity_id=activity_id, reason=reason)

    async def events_stream(
        self,
        *,
        session_id: str,
        activity_id: str | None = None,
        from_event_id: str | None = None,
    ) -> Any:
        return await asyncio.to_thread(
            self._client.events_stream,
            session_id=session_id,
            activity_id=activity_id,
            from_event_id=from_event_id,
        )

    async def events_read(self, *, stream_id: str, limit: int = 200) -> Any:
        return await asyncio.to_thread(self._client.events_read, stream_id=stream_id, limit=limit)

    async def events_ack(self, *, stream_id: str, event_ids: list[str]) -> Any:
        return await asyncio.to_thread(self._client.events_ack, stream_id=stream_id, event_ids=event_ids)
