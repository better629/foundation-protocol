"""Cost estimation from token usage."""

from __future__ import annotations

from dataclasses import dataclass

from .token_meter import TokenUsage


@dataclass(slots=True)
class CostModel:
    input_per_1k_tokens: float
    output_per_1k_tokens: float


class CostMeter:
    def __init__(self, model: CostModel) -> None:
        self._model = model

    def estimate(self, usage: TokenUsage) -> float:
        return (
            usage.input_tokens / 1000.0 * self._model.input_per_1k_tokens
            + usage.output_tokens / 1000.0 * self._model.output_per_1k_tokens
        )
