"""Core minimal profile."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CoreMinimalProfile:
    profile_id: str = "urn:fp:profile:core-minimal:v1"
    streaming: bool = False
    governance: bool = False
    economy: bool = False
