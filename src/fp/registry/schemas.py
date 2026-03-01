"""Schema registry."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class RegisteredSchema:
    schema_id: str
    version: str
    schema: dict[str, Any]
    sha256: str


class SchemaRegistry:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str], RegisteredSchema] = {}

    def register(self, schema_id: str, version: str, schema: dict[str, Any]) -> RegisteredSchema:
        canonical = json.dumps(schema, sort_keys=True, separators=(",", ":")).encode("utf-8")
        digest = hashlib.sha256(canonical).hexdigest()
        item = RegisteredSchema(schema_id=schema_id, version=version, schema=schema, sha256=digest)
        self._items[(schema_id, version)] = item
        return item

    def get(self, schema_id: str, version: str) -> RegisteredSchema | None:
        return self._items.get((schema_id, version))
