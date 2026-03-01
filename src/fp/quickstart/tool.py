"""Quickstart ToolNode API."""

from __future__ import annotations

from typing import Any, Callable

from fp.app import FPServer, make_default_entity
from fp.protocol import EntityKind


class ToolNode:
    def __init__(self, *, entity_id: str, server: FPServer | None = None) -> None:
        self.entity_id = entity_id
        self.server = server or FPServer()
        self.server.register_entity(make_default_entity(entity_id, EntityKind.TOOL, display_name=entity_id))

    def invoke(self, operation: str) -> Callable[[Callable[[dict[str, Any]], Any]], Callable[[dict[str, Any]], Any]]:
        def decorator(fn: Callable[[dict[str, Any]], Any]) -> Callable[[dict[str, Any]], Any]:
            self.server.register_operation(operation, fn)
            return fn

        return decorator

    def run_stdio(self) -> FPServer:
        return self.server

    def serve_http(self, host: str, port: int) -> FPServer:
        _ = (host, port)
        return self.server
