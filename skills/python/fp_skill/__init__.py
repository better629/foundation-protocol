"""FP Skill SDK (monorepo module, isolated from fp core package)."""

from __future__ import annotations

from .decorators import collect_operations, fp_agent, fp_operation, fp_service, fp_tool
from .errors import SkillError, SkillManifestError, SkillRuntimeError
from .manifest import (
    SkillAuth,
    SkillConnection,
    SkillDefaults,
    SkillEntity,
    SkillManifest,
    SkillOperation,
    load_manifest,
)
from .runtime import SkillRuntime

__all__ = [
    "SkillAuth",
    "SkillConnection",
    "SkillDefaults",
    "SkillEntity",
    "SkillError",
    "SkillManifest",
    "SkillManifestError",
    "SkillOperation",
    "SkillRuntime",
    "SkillRuntimeError",
    "collect_operations",
    "fp_agent",
    "fp_operation",
    "fp_service",
    "fp_tool",
    "load_manifest",
]
