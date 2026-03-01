"""Context compaction utilities for token-efficient result transport."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class CompactionResult:
    inline_payload: dict[str, Any] | None
    result_ref: str | None
    compacted: bool
    raw_bytes: int
    digest: str | None


class ContextCompactor:
    def __init__(self, *, max_inline_bytes: int | None = 4096, preview_chars: int = 160) -> None:
        if max_inline_bytes is not None and max_inline_bytes <= 0:
            raise ValueError("max_inline_bytes must be > 0 when provided")
        if preview_chars <= 0:
            raise ValueError("preview_chars must be > 0")
        self._max_inline_bytes = max_inline_bytes
        self._preview_chars = preview_chars

    def compact(self, payload: dict[str, Any]) -> CompactionResult:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        if self._max_inline_bytes is None or len(raw) <= self._max_inline_bytes:
            return CompactionResult(
                inline_payload=payload,
                result_ref=None,
                compacted=False,
                raw_bytes=len(raw),
                digest=None,
            )

        digest = hashlib.sha256(raw).hexdigest()
        preview = raw[: self._preview_chars].decode("utf-8", errors="replace")
        summary = {
            "compacted": True,
            "digest": digest,
            "bytes": len(raw),
            "preview": preview,
        }
        return CompactionResult(
            inline_payload=summary,
            result_ref=f"sha256://{digest}",
            compacted=True,
            raw_bytes=len(raw),
            digest=digest,
        )


__all__ = ["CompactionResult", "ContextCompactor"]
