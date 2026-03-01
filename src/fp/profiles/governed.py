"""Governed profile."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GovernedProfile:
    profile_id: str = "urn:fp:profile:governed:v1"
    streaming: bool = True
    governance: bool = True
    economy: bool = True
