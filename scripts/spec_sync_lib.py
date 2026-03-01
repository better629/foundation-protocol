#!/usr/bin/env python3
"""Utilities for deterministic spec-model sync artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _extract_core_defs(core: dict[str, Any]) -> list[str]:
    defs = core.get("$defs", {})
    if not isinstance(defs, dict):
        return []
    return sorted(str(name) for name in defs.keys())


def _extract_openrpc_methods(openrpc: dict[str, Any]) -> list[str]:
    methods = openrpc.get("methods", [])
    if not isinstance(methods, list):
        return []
    names: list[str] = []
    for method in methods:
        if isinstance(method, dict) and isinstance(method.get("name"), str):
            names.append(method["name"])
    return sorted(set(names))


def build_manifest(core_path: Path, openrpc_path: Path) -> dict[str, Any]:
    core = _load_json(core_path)
    openrpc = _load_json(openrpc_path)
    core_bytes = _canonical_json_bytes(core)
    openrpc_bytes = _canonical_json_bytes(openrpc)
    return {
        "schema_sync_version": 1,
        "core_schema_path": str(core_path),
        "openrpc_schema_path": str(openrpc_path),
        "core_schema_sha256": _sha256_bytes(core_bytes),
        "openrpc_schema_sha256": _sha256_bytes(openrpc_bytes),
        "core_defs": _extract_core_defs(core),
        "openrpc_methods": _extract_openrpc_methods(openrpc),
    }


def render_python_module(manifest: dict[str, Any]) -> str:
    core_defs = tuple(manifest["core_defs"])
    methods = tuple(manifest["openrpc_methods"])
    return (
        '"""Auto-generated spec sync manifest. Do not edit manually."""\n\n'
        "from __future__ import annotations\n\n"
        f"SCHEMA_SYNC_VERSION = {manifest['schema_sync_version']}\n"
        f"CORE_SCHEMA_PATH = {manifest['core_schema_path']!r}\n"
        f"OPENRPC_SCHEMA_PATH = {manifest['openrpc_schema_path']!r}\n"
        f"CORE_SCHEMA_SHA256 = {manifest['core_schema_sha256']!r}\n"
        f"OPENRPC_SCHEMA_SHA256 = {manifest['openrpc_schema_sha256']!r}\n"
        f"CORE_DEFS = {core_defs!r}\n"
        f"OPENRPC_METHODS = {methods!r}\n\n"
        "__all__ = [\n"
        '    "SCHEMA_SYNC_VERSION",\n'
        '    "CORE_SCHEMA_PATH",\n'
        '    "OPENRPC_SCHEMA_PATH",\n'
        '    "CORE_SCHEMA_SHA256",\n'
        '    "OPENRPC_SCHEMA_SHA256",\n'
        '    "CORE_DEFS",\n'
        '    "OPENRPC_METHODS",\n'
        "]\n"
    )


def render_manifest_json(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_outputs(
    manifest: dict[str, Any],
    *,
    output_py: Path,
    output_json: Path,
) -> None:
    output_py.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_py.write_text(render_python_module(manifest), encoding="utf-8")
    output_json.write_text(render_manifest_json(manifest), encoding="utf-8")


__all__ = [
    "build_manifest",
    "render_manifest_json",
    "render_python_module",
    "write_outputs",
]
