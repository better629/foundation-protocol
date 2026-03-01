"""Generic in-memory store primitives."""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from threading import RLock
from typing import Callable, Generic, TypeVar

K = TypeVar("K")
G = TypeVar("G")
V = TypeVar("V")


class InMemoryKVStore(Generic[K, V]):
    def __init__(self, *, key_fn: Callable[[V], K]) -> None:
        self._lock = RLock()
        self._items: dict[K, V] = {}
        self._key_fn = key_fn

    def put(self, value: V) -> None:
        key = self._key_fn(value)
        with self._lock:
            self._items[key] = deepcopy(value)

    def get(self, key: K) -> V | None:
        with self._lock:
            value = self._items.get(key)
            return deepcopy(value) if value is not None else None

    def list(self) -> list[V]:
        with self._lock:
            return [deepcopy(value) for value in self._items.values()]

    def remove(self, key: K) -> V | None:
        with self._lock:
            value = self._items.pop(key, None)
            return deepcopy(value) if value is not None else None


class InMemoryGroupedKVStore(Generic[K, G, V]):
    def __init__(self, *, key_fn: Callable[[V], K], group_fn: Callable[[V], G]) -> None:
        self._lock = RLock()
        self._items: dict[K, V] = {}
        self._groups: dict[G, set[K]] = defaultdict(set)
        self._key_fn = key_fn
        self._group_fn = group_fn

    def put(self, value: V) -> None:
        key = self._key_fn(value)
        group = self._group_fn(value)
        with self._lock:
            old = self._items.get(key)
            if old is not None:
                old_group = self._group_fn(old)
                if old_group != group:
                    self._groups[old_group].discard(key)
            self._items[key] = deepcopy(value)
            self._groups[group].add(key)

    def get(self, key: K) -> V | None:
        with self._lock:
            value = self._items.get(key)
            return deepcopy(value) if value is not None else None

    def list(self) -> list[V]:
        with self._lock:
            return [deepcopy(value) for value in self._items.values()]

    def by_group(self, group: G) -> list[V]:
        with self._lock:
            keys = sorted(self._groups.get(group, set()), key=lambda item: str(item))
            return [deepcopy(self._items[key]) for key in keys if key in self._items]

    def remove(self, key: K) -> V | None:
        with self._lock:
            value = self._items.pop(key, None)
            if value is None:
                return None
            group = self._group_fn(value)
            self._groups[group].discard(key)
            return deepcopy(value)


__all__ = ["InMemoryGroupedKVStore", "InMemoryKVStore"]
