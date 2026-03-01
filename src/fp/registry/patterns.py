"""Reusable interaction pattern registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class InteractionPattern:
    pattern_id: str
    description: str
    metadata: dict[str, Any] = field(default_factory=dict)


class PatternRegistry:
    def __init__(self) -> None:
        self._patterns: dict[str, InteractionPattern] = {}

    def register(self, pattern: InteractionPattern) -> InteractionPattern:
        self._patterns[pattern.pattern_id] = pattern
        return pattern

    def get(self, pattern_id: str) -> InteractionPattern | None:
        return self._patterns.get(pattern_id)

    def list(self) -> list[InteractionPattern]:
        return list(self._patterns.values())
