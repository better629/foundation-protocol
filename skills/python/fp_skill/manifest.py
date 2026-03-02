"""Skill manifest model and validation logic."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fp.protocol import EntityKind

from .errors import SkillManifestError

_HANDLER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_\.]*:[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(slots=True)
class SkillEntity:
    entity_id: str
    kind: str
    capability_purpose: list[str]
    display_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.entity_id.strip():
            raise SkillManifestError("entity.entity_id must be non-empty")
        valid_kinds = {item.value for item in EntityKind}
        if self.kind not in valid_kinds:
            raise SkillManifestError(f"entity.kind must be one of {sorted(valid_kinds)}")
        if not self.capability_purpose:
            raise SkillManifestError("entity.capability_purpose must not be empty")
        for item in self.capability_purpose:
            if not isinstance(item, str) or not item.strip():
                raise SkillManifestError("entity.capability_purpose must contain non-empty strings")


@dataclass(slots=True)
class SkillConnection:
    mode: str
    rpc_url: str | None = None
    timeout_seconds: float = 10.0
    keep_alive: bool = True

    def validate(self) -> None:
        if self.mode not in {"inproc", "http_jsonrpc"}:
            raise SkillManifestError("connection.mode must be inproc or http_jsonrpc")
        if self.mode == "http_jsonrpc" and (self.rpc_url is None or not self.rpc_url.strip()):
            raise SkillManifestError("connection.rpc_url is required for http_jsonrpc mode")
        if self.timeout_seconds <= 0:
            raise SkillManifestError("connection.timeout_seconds must be > 0")


@dataclass(slots=True)
class SkillAuth:
    mode: str = "none"
    token_env: str | None = None
    token: str | None = None

    def validate(self) -> None:
        if self.mode not in {"none", "bearer_env", "bearer_static"}:
            raise SkillManifestError("auth.mode must be none, bearer_env, or bearer_static")
        if self.mode == "bearer_env" and (self.token_env is None or not self.token_env.strip()):
            raise SkillManifestError("auth.token_env is required for bearer_env mode")
        if self.mode == "bearer_static" and (self.token is None or not self.token.strip()):
            raise SkillManifestError("auth.token is required for bearer_static mode")


@dataclass(slots=True)
class SkillDefaults:
    auto_session: bool = True
    policy_ref: str | None = None
    token_limit: int | None = None
    result_compaction_bytes: int | None = 4096
    default_roles: dict[str, list[str]] = field(default_factory=dict)

    def validate(self) -> None:
        if self.token_limit is not None and self.token_limit < 0:
            raise SkillManifestError("defaults.token_limit must be >= 0")
        if self.result_compaction_bytes is not None and self.result_compaction_bytes <= 0:
            raise SkillManifestError("defaults.result_compaction_bytes must be > 0")
        for entity_id, roles in self.default_roles.items():
            if not entity_id.strip():
                raise SkillManifestError("defaults.default_roles has empty entity key")
            if not roles:
                raise SkillManifestError(f"defaults.default_roles[{entity_id}] must not be empty")
            for role in roles:
                if not isinstance(role, str) or not role.strip():
                    raise SkillManifestError("default role values must be non-empty strings")


@dataclass(slots=True)
class SkillOperation:
    name: str
    handler: str
    description: str | None = None

    def validate(self) -> None:
        if not self.name.strip():
            raise SkillManifestError("operations[].name must be non-empty")
        if not self.handler.strip():
            raise SkillManifestError("operations[].handler must be non-empty")
        if _HANDLER_PATTERN.match(self.handler) is None:
            raise SkillManifestError(
                "operations[].handler must match module.path:function_name"
            )


@dataclass(slots=True)
class SkillManifest:
    skill_spec_version: str
    fp_version: str
    entity: SkillEntity
    connection: SkillConnection
    auth: SkillAuth
    defaults: SkillDefaults
    operations: list[SkillOperation]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "SkillManifest":
        if not isinstance(raw, dict):
            raise SkillManifestError("manifest must be a JSON object")
        try:
            entity_raw = raw.get("entity", {})
            connection_raw = raw.get("connection", {})
            auth_raw = raw.get("auth", {})
            defaults_raw = raw.get("defaults", {})
            operations_raw = list(raw.get("operations", []))
            manifest = cls(
                skill_spec_version=str(raw.get("skill_spec_version", "")),
                fp_version=str(raw.get("fp_version", "")),
                entity=SkillEntity(**dict(entity_raw)),
                connection=SkillConnection(**dict(connection_raw)),
                auth=SkillAuth(**dict(auth_raw)),
                defaults=SkillDefaults(**dict(defaults_raw)),
                operations=[SkillOperation(**dict(item)) for item in operations_raw],
            )
        except (TypeError, ValueError) as exc:
            raise SkillManifestError(f"manifest field shape is invalid: {exc}") from exc
        manifest.validate()
        return manifest

    def validate(self) -> None:
        if self.skill_spec_version != "0.1":
            raise SkillManifestError("skill_spec_version must be 0.1")
        if not self.fp_version.strip():
            raise SkillManifestError("fp_version must be non-empty")

        self.entity.validate()
        self.connection.validate()
        self.auth.validate()
        self.defaults.validate()

        if not self.operations:
            raise SkillManifestError("operations must contain at least one entry")

        seen: set[str] = set()
        for operation in self.operations:
            operation.validate()
            if operation.name in seen:
                raise SkillManifestError(f"duplicate operation name: {operation.name}")
            seen.add(operation.name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_spec_version": self.skill_spec_version,
            "fp_version": self.fp_version,
            "entity": {
                "entity_id": self.entity.entity_id,
                "kind": self.entity.kind,
                "display_name": self.entity.display_name,
                "capability_purpose": list(self.entity.capability_purpose),
                "metadata": dict(self.entity.metadata),
            },
            "connection": {
                "mode": self.connection.mode,
                "rpc_url": self.connection.rpc_url,
                "timeout_seconds": self.connection.timeout_seconds,
                "keep_alive": self.connection.keep_alive,
            },
            "auth": {
                "mode": self.auth.mode,
                "token_env": self.auth.token_env,
                "token": self.auth.token,
            },
            "defaults": {
                "auto_session": self.defaults.auto_session,
                "policy_ref": self.defaults.policy_ref,
                "token_limit": self.defaults.token_limit,
                "result_compaction_bytes": self.defaults.result_compaction_bytes,
                "default_roles": {k: list(v) for k, v in self.defaults.default_roles.items()},
            },
            "operations": [
                {
                    "name": operation.name,
                    "handler": operation.handler,
                    "description": operation.description,
                }
                for operation in self.operations
            ],
        }


def load_manifest(path: str | Path) -> SkillManifest:
    file_path = Path(path)
    if not file_path.exists():
        raise SkillManifestError(f"manifest file not found: {file_path}")

    suffix = file_path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        raise SkillManifestError(
            "YAML manifest requires external parser; use JSON (.json) in v0.1"
        )
    try:
        raw = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SkillManifestError(f"invalid JSON manifest: {exc}") from exc
    return SkillManifest.from_dict(raw)


__all__ = [
    "SkillAuth",
    "SkillConnection",
    "SkillDefaults",
    "SkillEntity",
    "SkillManifest",
    "SkillManifestError",
    "SkillOperation",
    "load_manifest",
]
