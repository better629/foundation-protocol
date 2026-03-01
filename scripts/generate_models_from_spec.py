#!/usr/bin/env python3
"""Generate deterministic schema-sync artifacts from FP specs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from spec_sync_lib import build_manifest, write_outputs


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", default="spec/fp-core.schema.json", help="Path to core schema")
    parser.add_argument("--openrpc", default="spec/fp-openrpc.json", help="Path to OpenRPC schema")
    parser.add_argument(
        "--output-py",
        default="src/fp/protocol/spec_manifest.py",
        help="Path to generated Python manifest module",
    )
    parser.add_argument(
        "--output-json",
        default="spec/.generated/spec-sync-manifest.json",
        help="Path to generated JSON manifest",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    core_path = Path(args.core).resolve()
    openrpc_path = Path(args.openrpc).resolve()
    output_py = Path(args.output_py).resolve()
    output_json = Path(args.output_json).resolve()

    for path in (core_path, openrpc_path):
        if not path.exists():
            print(f"ERROR: missing spec file: {path}")
            return 1

    manifest = build_manifest(core_path, openrpc_path)
    write_outputs(manifest, output_py=output_py, output_json=output_json)
    print(f"Generated: {output_py}")
    print(f"Generated: {output_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
