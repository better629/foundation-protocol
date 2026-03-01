"""Reliability primitives for remote transport calls."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass

from fp.protocol import FPError, FPErrorCode


@dataclass(slots=True)
class RetryPolicy:
    max_attempts: int = 1
    backoff_initial_seconds: float = 0.05
    backoff_max_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    jitter_ratio: float = 0.2
    retryable_http_status: frozenset[int] = frozenset({429, 500, 502, 503, 504})

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.backoff_initial_seconds < 0:
            raise ValueError("backoff_initial_seconds must be >= 0")
        if self.backoff_max_seconds < self.backoff_initial_seconds:
            raise ValueError("backoff_max_seconds must be >= backoff_initial_seconds")
        if self.backoff_multiplier < 1:
            raise ValueError("backoff_multiplier must be >= 1")
        if self.jitter_ratio < 0:
            raise ValueError("jitter_ratio must be >= 0")

    def delay_for_attempt(self, attempt_index: int) -> float:
        # attempt_index is 1-based retry index (1 => first retry after initial failure).
        base = min(
            self.backoff_max_seconds,
            self.backoff_initial_seconds * (self.backoff_multiplier ** max(0, attempt_index - 1)),
        )
        if base <= 0 or self.jitter_ratio == 0:
            return base
        jitter = base * self.jitter_ratio
        return max(0.0, base + random.uniform(-jitter, jitter))


@dataclass(slots=True)
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout_seconds: float = 5.0

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.recovery_timeout_seconds < 0:
            raise ValueError("recovery_timeout_seconds must be >= 0")


class CircuitBreaker:
    def __init__(self, config: CircuitBreakerConfig | None = None) -> None:
        self._config = config or CircuitBreakerConfig()
        self._failure_count = 0
        self._opened_at: float | None = None

    def before_call(self) -> None:
        if self._opened_at is None:
            return
        now = time.monotonic()
        elapsed = now - self._opened_at
        if elapsed >= self._config.recovery_timeout_seconds:
            # half-open trial path: allow one call, keep counter as-is until result.
            return
        raise FPError(
            FPErrorCode.RATE_LIMITED,
            message="remote transport circuit is open",
            details={"retry_after_seconds": round(self._config.recovery_timeout_seconds - elapsed, 6)},
            retryable=True,
        )

    def record_success(self) -> None:
        self._failure_count = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failure_count += 1
        if self._failure_count >= self._config.failure_threshold:
            self._opened_at = time.monotonic()


__all__ = ["CircuitBreaker", "CircuitBreakerConfig", "RetryPolicy"]
