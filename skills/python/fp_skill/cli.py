"""CLI for FP Skill manifest validation and bootstrap checks."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from enum import Enum

from fp.app import FPClient
from fp.federation import InMemoryDirectory
from fp.transport import FPHTTPPublishedServer

from .errors import SkillError, SkillManifestError
from .manifest import load_manifest
from .runtime import SkillRuntime


def _cmd_validate(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.manifest)
    print(json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    print("\n[ok] skill manifest validated")
    return 0


def _cmd_smoke(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.manifest)
    runtime = SkillRuntime(manifest)
    loaded = runtime.load_manifest_operations()
    print(f"[ok] loaded operations: {', '.join(sorted(loaded.keys()))}")
    if args.operation:
        if args.operation not in loaded:
            raise SkillManifestError(f"operation not declared in manifest: {args.operation}")
        payload = json.loads(args.payload) if args.payload else {}
        result = runtime.invoke(
            operation=args.operation,
            input_payload=payload,
            idempotency_key=args.idempotency_key,
        )
        print(json.dumps(_jsonable(result), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.manifest)
    runtime = SkillRuntime(manifest)
    loaded = runtime.load_manifest_operations()

    if args.duration_seconds is not None and args.duration_seconds < 0:
        raise SkillManifestError("duration-seconds must be >= 0")
    if args.card_ttl_seconds <= 0:
        raise SkillManifestError("card-ttl-seconds must be > 0")

    publish_entity_id = args.publish_entity_id or manifest.entity.entity_id
    with FPHTTPPublishedServer(
        runtime.server,
        publish_entity_id=publish_entity_id,
        host=args.host,
        port=args.port,
        rpc_path=args.rpc_path,
        well_known_path=args.well_known_path,
        card_ttl_seconds=args.card_ttl_seconds,
    ) as published:
        ping = FPClient.from_http_jsonrpc(
            published.rpc_url,
            timeout_seconds=args.timeout_seconds,
            keep_alive=False,
        ).ping()
        self_check = {"ping_ok": bool(ping.get("ok") is True), "fp_version": ping.get("fp_version")}

        directory_payload: dict[str, object] = {"mode": args.directory, "published": False}
        if args.directory == "inmemory":
            directory = InMemoryDirectory()
            directory.publish(published.server_card)
            resolved = directory.resolve(publish_entity_id)
            directory_payload = {
                "mode": "inmemory",
                "published": True,
                "resolved_entity_id": resolved.entity_id,
                "resolved_card_id": resolved.card_id,
            }

        payload = {
            "entity_id": manifest.entity.entity_id,
            "publish_entity_id": publish_entity_id,
            "rpc_url": published.rpc_url,
            "well_known_url": published.well_known_url,
            "server_card": published.server_card.to_dict(),
            "operations": sorted(loaded.keys()),
            "self_check": self_check,
            "directory": directory_payload,
        }

        if args.announce_file is not None:
            args.announce_file.parent.mkdir(parents=True, exist_ok=True)
            args.announce_file.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))

        if args.duration_seconds is not None:
            time.sleep(args.duration_seconds)
            return 0

        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return 0


def _jsonable(value: object) -> object:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, set):
        return [_jsonable(item) for item in sorted(value)]
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fp-skill", description="FP Skill tooling")
    sub = parser.add_subparsers(dest="cmd", required=True)

    validate = sub.add_parser("validate", help="Validate manifest and print normalized JSON")
    validate.add_argument("manifest", type=Path)
    validate.set_defaults(func=_cmd_validate)

    smoke = sub.add_parser("smoke", help="Load manifest, register operations, optional local invoke")
    smoke.add_argument("manifest", type=Path)
    smoke.add_argument("--operation", type=str, default=None)
    smoke.add_argument("--payload", type=str, default="{}")
    smoke.add_argument("--idempotency-key", type=str, default=None)
    smoke.set_defaults(func=_cmd_smoke)

    serve = sub.add_parser("serve", help="Load manifest operations and publish HTTP JSON-RPC server")
    serve.add_argument("manifest", type=Path)
    serve.add_argument("--host", type=str, default="127.0.0.1")
    serve.add_argument("--port", type=int, default=0)
    serve.add_argument("--rpc-path", type=str, default="/rpc")
    serve.add_argument("--well-known-path", type=str, default="/.well-known/fp-server.json")
    serve.add_argument("--publish-entity-id", type=str, default=None)
    serve.add_argument("--card-ttl-seconds", type=int, default=600)
    serve.add_argument("--timeout-seconds", type=float, default=5.0)
    serve.add_argument("--duration-seconds", type=float, default=None)
    serve.add_argument("--directory", choices=["none", "inmemory"], default="none")
    serve.add_argument("--announce-file", type=Path, default=None)
    serve.set_defaults(func=_cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except SkillError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
