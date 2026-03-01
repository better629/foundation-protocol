"""Quickstart ResourceNode API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fp.app import FPServer, make_default_entity
from fp.protocol import EntityKind, FPError, FPErrorCode


class ResourceNode:
    def __init__(self, *, entity_id: str, server: FPServer | None = None) -> None:
        self.entity_id = entity_id
        self.server = server or FPServer()
        self._mounts: dict[str, Path] = {}
        self.server.register_entity(make_default_entity(entity_id, EntityKind.RESOURCE, display_name=entity_id))

    def mount_file(self, resource_uri: str, path: str) -> None:
        self._mounts[resource_uri] = Path(path)

    def read(self, resource_uri: str) -> str:
        path = self._mounts.get(resource_uri)
        if path is None:
            raise FPError(FPErrorCode.NOT_FOUND, f"resource not mounted: {resource_uri}")
        return path.read_text(encoding="utf-8")

    def serve_http(self, host: str, port: int) -> FPServer:
        _ = (host, port)
        return self.server
