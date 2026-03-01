"""Operation dispatch engine."""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass, field
from typing import Any, Callable

from fp.protocol import FPError, FPErrorCode

Handler = Callable[..., Any]
_SyncInvoker = Callable[["DispatchContext", dict[str, Any]], Any]


@dataclass(slots=True)
class DispatchContext:
    session_id: str
    activity_id: str
    operation: str
    actor_entity_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class _RegisteredOperation:
    invoke: _SyncInvoker
    schema: dict[str, Any] | None = None


class DispatchEngine:
    def __init__(self) -> None:
        self._operations: dict[str, _RegisteredOperation] = {}

    def register(self, operation: str, handler: Handler) -> None:
        invoke = _build_invoker(handler)
        schema = _extract_schema(handler)
        self._operations[operation] = _RegisteredOperation(invoke=invoke, schema=schema)

    def has_handler(self, operation: str) -> bool:
        return operation in self._operations

    def schema_for(self, operation: str) -> dict[str, Any]:
        registered = self._operations.get(operation)
        if registered is None:
            raise FPError(FPErrorCode.NOT_FOUND, f"operation handler not found: {operation}")
        return dict(registered.schema or {})

    def operation_schemas(self) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for operation, registered in self._operations.items():
            if registered.schema is not None:
                out[operation] = dict(registered.schema)
        return out

    def execute(self, *, context: DispatchContext, input_payload: dict[str, Any]) -> Any:
        registered = self._operations.get(context.operation)
        if registered is None:
            raise FPError(FPErrorCode.NOT_FOUND, f"operation handler not found: {context.operation}")

        output = registered.invoke(context, input_payload)
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


class AsyncDispatchEngine(DispatchEngine):
    async def execute(self, *, context: DispatchContext, input_payload: dict[str, Any]) -> Any:
        registered = self._operations.get(context.operation)
        if registered is None:
            raise FPError(FPErrorCode.NOT_FOUND, f"operation handler not found: {context.operation}")
        output = registered.invoke(context, input_payload)
        if inspect.isawaitable(output):
            return await output
        return output


def _build_invoker(handler: Handler) -> _SyncInvoker:
    typed_invoke = getattr(handler, "__fp_invoke__", None)
    if callable(typed_invoke):
        return lambda context, payload: typed_invoke(context, payload)

    signature = inspect.signature(handler)
    parameters = list(signature.parameters.values())
    parameter_count = len(parameters)
    if parameter_count == 0:
        return lambda context, payload: handler()  # type: ignore[misc]
    if parameter_count >= 1:
        first_name = parameters[0].name.lower()
        if first_name in {"ctx", "context"}:
            if parameter_count == 1:
                return lambda context, payload: handler(context)  # type: ignore[misc]
            return lambda context, payload: handler(context, payload)  # type: ignore[misc]
        return lambda context, payload: handler(payload)  # type: ignore[misc]
    return lambda context, payload: handler(payload)  # pragma: no cover


def _extract_schema(handler: Handler) -> dict[str, Any] | None:
    schema = getattr(handler, "__fp_schema__", None)
    if isinstance(schema, dict):
        return schema
    return None


__all__ = ["AsyncDispatchEngine", "DispatchContext", "DispatchEngine"]
