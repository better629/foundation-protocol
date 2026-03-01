"""Idempotency key guard."""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Generic, TypeVar

from fp.protocol.errors import FPError, FPErrorCode

T = TypeVar("T")


@dataclass(slots=True)
class IdempotentResult(Generic[T]):
    hit: bool
    value: T


@dataclass(slots=True)
class _Entry:
    fingerprint: str
    value: object


class IdempotencyGuard:
    def __init__(self) -> None:
        self._lock = RLock()
        self._cache: dict[str, _Entry] = {}

    def check(self, key: str, *, fingerprint: str | None = None) -> IdempotentResult[object] | None:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if fingerprint is not None and entry.fingerprint != fingerprint:
                raise FPError(
                    FPErrorCode.CONFLICT,
                    message="idempotency key reused with different request payload",
                    details={"idempotency_key": key},
                )
            return IdempotentResult(hit=True, value=entry.value)

    def store(self, key: str, value: object, *, fingerprint: str) -> None:
        with self._lock:
            self._cache[key] = _Entry(fingerprint=fingerprint, value=value)
