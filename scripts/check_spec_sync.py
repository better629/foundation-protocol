#!/usr/bin/env python3
"""Check whether generated schema-sync artifacts are in sync with specs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from spec_sync_lib import build_manifest, render_manifest_json, render_python_module


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", default="spec/fp-core.schema.json", help="Path to core schema")
    parser.add_argument("--openrpc", default="spec/fp-openrpc.json", help="Path to OpenRPC schema")
    parser.add_argument(
        "--generated-py",
        default="src/fp/protocol/spec_manifest.py",
        help="Path to generated Python manifest module",
    )
    parser.add_argument(
        "--manifest-json",
        default="spec/.generated/spec-sync-manifest.json",
        help="Path to generated JSON manifest",
    )
    return parser.parse_args()


def check_sync(
    *,
    core_path: Path,
    openrpc_path: Path,
    generated_py_path: Path,
    manifest_json_path: Path,
) -> tuple[bool, list[str]]:
    messages: list[str] = []
    for path in (core_path, openrpc_path):
        if not path.exists():
            messages.append(f"missing spec file: {path}")
    if messages:
        return False, messages

    manifest = build_manifest(core_path, openrpc_path)
    expected_py = render_python_module(manifest)
    expected_json = render_manifest_json(manifest)

    if not generated_py_path.exists():
        messages.append(f"missing generated module: {generated_py_path}")
    else:
        actual_py = generated_py_path.read_text(encoding="utf-8")
        if actual_py != expected_py:
            messages.append(f"generated module drift detected: {generated_py_path}")

    if not manifest_json_path.exists():
        messages.append(f"missing generated manifest: {manifest_json_path}")
    else:
        actual_json = manifest_json_path.read_text(encoding="utf-8")
        if actual_json != expected_json:
            messages.append(f"generated manifest drift detected: {manifest_json_path}")

    return len(messages) == 0, messages


def main() -> int:
    args = _parse_args()
    ok, messages = check_sync(
        core_path=Path(args.core).resolve(),
        openrpc_path=Path(args.openrpc).resolve(),
        generated_py_path=Path(args.generated_py).resolve(),
        manifest_json_path=Path(args.manifest_json).resolve(),
    )
    if ok:
        print("Spec sync check passed.")
        return 0

    for message in messages:
        print(f"ERROR: {message}")
    print("Run: python scripts/generate_models_from_spec.py")
    return 1


if __name__ == "__main__":
    sys.exit(main())
