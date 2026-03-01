"""Relationship edge primitives for FP graph-first model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock

from fp.protocol import utc_now


@dataclass(slots=True)
class Relationship:
    relation_id: str
    source_entity_id: str
    target_entity_id: str
    relation_type: str
    metadata: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)


class RelationshipGraph:
    def __init__(self) -> None:
        self._lock = RLock()
        self._relations: dict[str, Relationship] = {}

    def add(self, relation: Relationship) -> None:
        with self._lock:
            self._relations[relation.relation_id] = relation

    def get(self, relation_id: str) -> Relationship | None:
        with self._lock:
            return self._relations.get(relation_id)

    def list_for_entity(self, entity_id: str) -> list[Relationship]:
        with self._lock:
            return [
                relation
                for relation in self._relations.values()
                if relation.source_entity_id == entity_id or relation.target_entity_id == entity_id
            ]
