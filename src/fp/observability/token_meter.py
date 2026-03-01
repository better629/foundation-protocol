"""Token accounting helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int


class TokenMeter:
    """Lightweight token approximation for protocol-level budgeting.

    This intentionally avoids provider-specific tokenizers and uses a stable heuristic
    to keep runtime overhead minimal.
    """

    @staticmethod
    def estimate_payload_tokens(payload: dict[str, Any]) -> int:
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        # Approximation: ~1 token per 4 chars for mixed natural language/JSON payloads.
        return max(1, len(text) // 4)

    def measure(self, *, input_payload: dict[str, Any], output_payload: dict[str, Any]) -> TokenUsage:
        return TokenUsage(
            input_tokens=self.estimate_payload_tokens(input_payload),
            output_tokens=self.estimate_payload_tokens(output_payload),
        )
