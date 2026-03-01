"""Core streaming profile."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CoreStreamingProfile:
    profile_id: str = "urn:fp:profile:core-streaming:v1"
    streaming: bool = True
    governance: bool = False
    economy: bool = False
