"""Entity registry helpers."""

from __future__ import annotations

from fp.protocol import Entity, FPError, FPErrorCode
from fp.stores.interfaces import EntityStore


class EntityRegistry:
    def __init__(self, store: EntityStore) -> None:
        self._store = store

    def register(self, entity: Entity) -> Entity:
        existing = self._store.get(entity.entity_id)
        if existing is not None:
            raise FPError(
                FPErrorCode.ALREADY_EXISTS,
                message=f"entity already exists: {entity.entity_id}",
            )
        self._store.put(entity)
        return entity

    def upsert(self, entity: Entity) -> Entity:
        self._store.put(entity)
        return entity

    def get(self, entity_id: str) -> Entity:
        entity = self._store.get(entity_id)
        if entity is None:
            raise FPError(FPErrorCode.NOT_FOUND, message=f"entity not found: {entity_id}")
        return entity

    def search(self, *, query: str, kind: str | None = None, limit: int = 50) -> list[Entity]:
        normalized = query.strip().lower()
        results: list[Entity] = []
        for entity in self._store.list():
            if kind and entity.kind.value != kind:
                continue
            haystack = " ".join(
                [
                    entity.entity_id,
                    entity.display_name or "",
                    " ".join(entity.capability_summary.purpose),
                ]
            ).lower()
            if normalized in haystack:
                results.append(entity)
            if len(results) >= limit:
                break
        return results
