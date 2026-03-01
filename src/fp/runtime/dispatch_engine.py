"""Operation dispatch engine."""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass, field
from typing import Any, Callable

from fp.protocol import FPError, FPErrorCode

Handler = Callable[[dict[str, Any]], Any]


@dataclass(slots=True)
class DispatchContext:
    session_id: str
    activity_id: str
    operation: str
    actor_entity_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


class DispatchEngine:
    def __init__(self) -> None:
        self._operation_handlers: dict[str, Handler] = {}

    def register(self, operation: str, handler: Handler) -> None:
        self._operation_handlers[operation] = handler

    def has_handler(self, operation: str) -> bool:
        return operation in self._operation_handlers

    def execute(self, *, context: DispatchContext, input_payload: dict[str, Any]) -> Any:
        handler = self._operation_handlers.get(context.operation)
        if handler is None:
            raise FPError(FPErrorCode.NOT_FOUND, f"operation handler not found: {context.operation}")

        output = handler(input_payload)
        if inspect.isawaitable(output):
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                return asyncio.run(output)
            raise FPError(
                FPErrorCode.INTERNAL_ERROR,
                message=(
                    "cannot execute async handler from sync context while event loop is running; "
                    "register a sync handler or call through async runtime entrypoints"
                ),
            )
        return output
