"""Async FP client API."""

from __future__ import annotations

import asyncio
import ssl
from typing import Any

from fp.app.client import FPClient
from fp.protocol import ActivityState, SessionBudget
from fp.transport.client_http_jsonrpc import HTTPJSONRPCClientTransport
from fp.transport.client_inproc import InProcessJSONRPCClientTransport
from fp.transport.reliability import CircuitBreaker, RetryPolicy

from .async_server import AsyncFPServer


class AsyncFPClient:
    def __init__(self, client: FPClient) -> None:
        self._client = client

    @classmethod
    def from_inproc(cls, server: AsyncFPServer | Any) -> "AsyncFPClient":
        if isinstance(server, AsyncFPServer):
            transport = InProcessJSONRPCClientTransport(server.sync_server)
            return cls(FPClient(transport=transport))
        transport = InProcessJSONRPCClientTransport(server)
        return cls(FPClient(transport=transport))

    @classmethod
    def from_http_jsonrpc(
        cls,
        rpc_url: str,
        *,
        timeout_seconds: float = 10.0,
        headers: dict[str, str] | None = None,
        ssl_context: ssl.SSLContext | None = None,
        retry_policy: RetryPolicy | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        keep_alive: bool = True,
    ) -> "AsyncFPClient":
        transport = HTTPJSONRPCClientTransport(
            rpc_url,
            timeout_seconds=timeout_seconds,
            headers=headers,
            ssl_context=ssl_context,
            retry_policy=retry_policy,
            circuit_breaker=circuit_breaker,
            keep_alive=keep_alive,
        )
        return cls(FPClient(transport=transport))

    def close(self) -> None:
        transport = getattr(self._client, "_transport", None)
        if transport is None:
            return
        close_fn = getattr(transport, "close", None)
        if callable(close_fn):
            close_fn()

    async def aclose(self) -> None:
        await asyncio.to_thread(self.close)

    async def initialize(self, *, supported_versions: list[str], entity_id: str, profile: str | None = None) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._client.initialize,
            supported_versions=supported_versions,
            entity_id=entity_id,
            profile=profile,
        )

    async def ping(self) -> dict[str, Any]:
        return await asyncio.to_thread(self._client.ping)

    async def register_entity(self, entity: Any) -> dict[str, Any]:
        return await asyncio.to_thread(self._client.register_entity, entity)

    async def get_entity(self, entity_id: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._client.get_entity, entity_id)

    async def session_create(
        self,
        *,
        participants: set[str],
        roles: dict[str, set[str]],
        policy_ref: str | None = None,
        budget: SessionBudget | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._client.session_create,
            participants=participants,
            roles=roles,
            policy_ref=policy_ref,
            budget=budget,
            session_id=session_id,
        )

    async def session_get(self, session_id: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._client.session_get, session_id)

    async def session_list_page(self, *, limit: int = 100, cursor: str | None = None) -> dict[str, Any]:
        return await asyncio.to_thread(self._client.session_list_page, limit=limit, cursor=cursor)

    async def activity_start(
        self,
        *,
        session_id: str,
        owner_entity_id: str,
        initiator_entity_id: str,
        operation: str,
        input_payload: dict[str, Any],
        activity_id: str | None = None,
        idempotency_key: str | None = None,
        auto_execute: bool = True,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._client.activity_start,
            session_id=session_id,
            owner_entity_id=owner_entity_id,
            initiator_entity_id=initiator_entity_id,
            operation=operation,
            input_payload=input_payload,
            activity_id=activity_id,
            idempotency_key=idempotency_key,
            auto_execute=auto_execute,
        )

    async def activity_result(self, *, activity_id: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._client.activity_result, activity_id=activity_id)

    async def activity_list_page(
        self,
        *,
        session_id: str | None = None,
        state: str | None = None,
        owner_entity_id: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._client.activity_list_page,
            session_id=session_id,
            state=state,
            owner_entity_id=owner_entity_id,
            limit=limit,
            cursor=cursor,
        )

    async def activity_update(
        self,
        *,
        activity_id: str,
        state: ActivityState,
        status_message: str | None = None,
        patch: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._client.activity_update,
            activity_id=activity_id,
            state=state,
            status_message=status_message,
            patch=patch,
        )

    async def activity_cancel(self, *, activity_id: str, reason: str | None = None) -> dict[str, Any]:
        return await asyncio.to_thread(self._client.activity_cancel, activity_id=activity_id, reason=reason)

    async def events_stream(
        self,
        *,
        session_id: str,
        activity_id: str | None = None,
        from_event_id: str | None = None,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._client.events_stream,
            session_id=session_id,
            activity_id=activity_id,
            from_event_id=from_event_id,
        )

    async def events_read(self, *, stream_id: str, limit: int = 200) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._client.events_read, stream_id=stream_id, limit=limit)

    async def events_ack(self, *, stream_id: str, event_ids: list[str]) -> dict[str, Any]:
        return await asyncio.to_thread(self._client.events_ack, stream_id=stream_id, event_ids=event_ids)
