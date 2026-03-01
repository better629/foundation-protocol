#!/usr/bin/env python3
"""Validate Foundation Protocol machine-readable spec artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


REQUIRED_CORE_DEFS = {
    "Identifier",
    "Entity",
    "Organization",
    "Membership",
    "Session",
    "Activity",
    "Event",
    "Envelope",
    "MeterRecord",
    "Receipt",
    "Settlement",
    "Dispute",
    "ProvenanceRecord",
    "Error",
}

REQUIRED_OPENRPC_METHODS = {
    "fp/initialize",
    "fp/initialized",
    "fp/ping",
    "fp/entities.get",
    "fp/entities.search",
    "fp/orgs.create",
    "fp/orgs.get",
    "fp/orgs.members.add",
    "fp/orgs.members.remove",
    "fp/orgs.roles.grant",
    "fp/orgs.roles.revoke",
    "fp/sessions.create",
    "fp/sessions.join",
    "fp/sessions.update",
    "fp/sessions.leave",
    "fp/sessions.close",
    "fp/sessions.get",
    "fp/activities.start",
    "fp/activities.update",
    "fp/activities.get",
    "fp/activities.cancel",
    "fp/activities.result",
    "fp/activities.list",
    "fp/events.stream",
    "fp/events.resubscribe",
    "fp/events.ack",
    "fp/events.pushConfig.set",
    "fp/events.pushConfig.get",
    "fp/events.pushConfig.list",
    "fp/events.pushConfig.delete",
}


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive path
        raise ValueError(f"failed to read JSON: {path}: {exc}") from exc


def _iter_refs(node: Any, context: str = "$") -> Iterable[tuple[str, str]]:
    if isinstance(node, dict):
        for key, value in node.items():
            next_ctx = f"{context}.{key}"
            if key == "$ref" and isinstance(value, str):
                yield value, next_ctx
            else:
                yield from _iter_refs(value, next_ctx)
    elif isinstance(node, list):
        for idx, value in enumerate(node):
            yield from _iter_refs(value, f"{context}[{idx}]")


def _decode_pointer_token(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def _resolve_pointer(doc: Any, pointer: str) -> Any:
    if pointer in {"", "#"}:
        return doc
    if not pointer.startswith("#/"):
        raise ValueError(f"unsupported JSON pointer: {pointer}")

    current: Any = doc
    for raw_token in pointer[2:].split("/"):
        token = _decode_pointer_token(raw_token)
        if isinstance(current, dict):
            if token not in current:
                raise KeyError(token)
            current = current[token]
            continue
        if isinstance(current, list):
            if not token.isdigit():
                raise KeyError(token)
            idx = int(token)
            if idx < 0 or idx >= len(current):
                raise IndexError(idx)
            current = current[idx]
            continue
        raise TypeError(f"pointer stepped into non-container at token {token!r}")

    return current


_URL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")
_FP_METHOD_RE = re.compile(r"`(fp/[A-Za-z0-9._/]+)`")


def _validate_refs(doc: Any, doc_path: Path, cache: dict[Path, Any], errors: list[str]) -> None:
    for ref, where in _iter_refs(doc):
        if ref.startswith("#"):
            try:
                _resolve_pointer(doc, ref)
            except Exception as exc:  # pragma: no cover - error path
                errors.append(f"{doc_path}: unresolved local $ref {ref!r} at {where}: {exc}")
            continue

        target_spec, has_hash, fragment = ref.partition("#")
        if _URL_RE.match(target_spec):
            # External URL refs are allowed but not resolved by this local checker.
            continue

        target_path = (doc_path.parent / target_spec).resolve()
        if not target_path.exists():
            errors.append(f"{doc_path}: unresolved file $ref {ref!r} at {where}: missing {target_path}")
            continue

        target_doc = cache.setdefault(target_path, _load_json(target_path))
        if has_hash:
            try:
                _resolve_pointer(target_doc, f"#{fragment}")
            except Exception as exc:  # pragma: no cover - error path
                errors.append(
                    f"{doc_path}: unresolved fragment in $ref {ref!r} at {where}: {exc}"
                )


def _validate_core_schema(core: Any, core_path: Path, errors: list[str], warnings: list[str]) -> None:
    if not isinstance(core, dict):
        errors.append(f"{core_path}: root must be a JSON object")
        return

    if "$schema" not in core:
        errors.append(f"{core_path}: missing required top-level key '$schema'")
    defs = core.get("$defs")
    if not isinstance(defs, dict):
        errors.append(f"{core_path}: missing or invalid '$defs' object")
        return

    missing_defs = sorted(REQUIRED_CORE_DEFS - set(defs.keys()))
    if missing_defs:
        errors.append(f"{core_path}: missing required $defs: {', '.join(missing_defs)}")

    if core.get("type") != "object":
        warnings.append(f"{core_path}: root type is not 'object'")


def _validate_openrpc(openrpc: Any, openrpc_path: Path, errors: list[str], warnings: list[str]) -> None:
    if not isinstance(openrpc, dict):
        errors.append(f"{openrpc_path}: root must be a JSON object")
        return

    for key in ("openrpc", "info", "methods", "components"):
        if key not in openrpc:
            errors.append(f"{openrpc_path}: missing required top-level key {key!r}")

    methods = openrpc.get("methods")
    if not isinstance(methods, list):
        errors.append(f"{openrpc_path}: 'methods' must be an array")
        return
    if not methods:
        errors.append(f"{openrpc_path}: 'methods' array must not be empty")
        return

    seen: set[str] = set()
    names: set[str] = set()
    for idx, method in enumerate(methods):
        if not isinstance(method, dict):
            errors.append(f"{openrpc_path}: methods[{idx}] must be an object")
            continue

        name = method.get("name")
        if not isinstance(name, str) or not name:
            errors.append(f"{openrpc_path}: methods[{idx}] missing valid 'name'")
        elif name in seen:
            errors.append(f"{openrpc_path}: duplicate method name {name!r}")
        else:
            seen.add(name)
            names.add(name)

        params = method.get("params")
        if not isinstance(params, list):
            errors.append(f"{openrpc_path}: method {name!r} missing 'params' array")

        if name != "fp/initialized" and "result" not in method:
            errors.append(f"{openrpc_path}: method {name!r} missing 'result'")
        if (
            name == "fp/initialized"
            and method.get("x-notification") is not True
            and "result" in method
        ):
            warnings.append(
                f"{openrpc_path}: method 'fp/initialized' includes a result; "
                "JSON-RPC notifications usually omit results"
            )

    missing_methods = sorted(REQUIRED_OPENRPC_METHODS - names)
    if missing_methods:
        errors.append(f"{openrpc_path}: missing required methods: {', '.join(missing_methods)}")

    extra_methods = sorted(names - REQUIRED_OPENRPC_METHODS)
    if extra_methods:
        warnings.append(
            f"{openrpc_path}: additional methods beyond v0.1 core set: "
            f"{', '.join(extra_methods)}"
        )

    components = openrpc.get("components")
    if isinstance(components, dict):
        if "schemas" not in components:
            errors.append(f"{openrpc_path}: components.schemas is required")
        if "errors" not in components:
            warnings.append(f"{openrpc_path}: components.errors is recommended")
    else:
        errors.append(f"{openrpc_path}: components must be an object")


def _validate_jsonschema_meta(core: Any, core_path: Path, warnings: list[str], errors: list[str]) -> None:
    try:
        from jsonschema import validators
    except Exception:
        warnings.append(
            f"{core_path}: python package 'jsonschema' not installed; skipped Draft 2020-12 "
            "meta-schema validation"
        )
        return

    try:
        validator_cls = validators.validator_for(core)
        validator_cls.check_schema(core)
    except Exception as exc:  # pragma: no cover - depends on external package
        errors.append(f"{core_path}: failed Draft 2020-12 schema check: {exc}")


def _extract_fp_methods_from_markdown(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    return {m.group(1) for m in _FP_METHOD_RE.finditer(text)}


def _validate_draft_alignment(
    draft_path: Path, openrpc_method_names: set[str], errors: list[str], warnings: list[str]
) -> None:
    if not draft_path.exists():
        warnings.append(f"{draft_path}: draft document not found, skipped method alignment check")
        return

    try:
        draft_methods = _extract_fp_methods_from_markdown(draft_path)
    except Exception as exc:  # pragma: no cover - defensive path
        warnings.append(f"{draft_path}: failed to parse draft methods: {exc}")
        return

    if not draft_methods:
        warnings.append(f"{draft_path}: no `fp/*` methods found in markdown")
        return

    missing_in_openrpc = sorted(draft_methods - openrpc_method_names)
    if missing_in_openrpc:
        errors.append(
            f"{draft_path}: methods documented in draft but missing in OpenRPC: "
            f"{', '.join(missing_in_openrpc)}"
        )

    missing_in_draft = sorted(openrpc_method_names - draft_methods)
    if missing_in_draft:
        warnings.append(
            f"{draft_path}: methods in OpenRPC but not listed in draft markdown: "
            f"{', '.join(missing_in_draft)}"
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--core",
        default="spec/fp-core.schema.json",
        help="Path to fp-core JSON Schema",
    )
    parser.add_argument(
        "--openrpc",
        default="spec/fp-openrpc.json",
        help="Path to fp OpenRPC document",
    )
    parser.add_argument(
        "--draft",
        default="docs/foundation-protocol-spec-draft.md",
        help="Path to fp draft markdown document for method alignment checks",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    core_path = Path(args.core).resolve()
    openrpc_path = Path(args.openrpc).resolve()
    draft_path = Path(args.draft).resolve()

    errors: list[str] = []
    warnings: list[str] = []

    for path in (core_path, openrpc_path):
        if not path.exists():
            errors.append(f"missing required file: {path}")

    if errors:
        for msg in errors:
            print(f"ERROR: {msg}")
        return 1

    try:
        core = _load_json(core_path)
        openrpc = _load_json(openrpc_path)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    _validate_core_schema(core, core_path, errors, warnings)
    _validate_openrpc(openrpc, openrpc_path, errors, warnings)
    _validate_jsonschema_meta(core, core_path, warnings, errors)

    cache: dict[Path, Any] = {core_path: core, openrpc_path: openrpc}
    _validate_refs(core, core_path, cache, errors)
    _validate_refs(openrpc, openrpc_path, cache, errors)

    openrpc_method_names = {
        method.get("name")
        for method in openrpc.get("methods", [])
        if isinstance(method, dict) and isinstance(method.get("name"), str)
    }
    _validate_draft_alignment(draft_path, openrpc_method_names, errors, warnings)

    for msg in warnings:
        print(f"WARN: {msg}")
    for msg in errors:
        print(f"ERROR: {msg}")

    if errors:
        print("\nSpec validation failed.")
        return 1

    print("Spec validation passed.")
    if warnings:
        print(f"Completed with {len(warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
