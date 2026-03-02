"""Error types for FP Skill runtime and manifest validation."""

from __future__ import annotations


class SkillError(Exception):
    """Base error for FP Skill package."""


class SkillManifestError(SkillError):
    """Raised when manifest loading or validation fails."""


class SkillRuntimeError(SkillError):
    """Raised when skill runtime bootstrapping fails."""
