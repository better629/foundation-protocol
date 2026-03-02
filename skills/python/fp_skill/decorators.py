"""Decorators and discovery helpers for FP Skill operations."""

from __future__ import annotations

from typing import Any, Callable, Mapping

_OPERATION_ATTR = "__fp_skill_operation__"
_ENTITY_ATTR = "__fp_skill_entity__"


def fp_operation(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    if not name.strip():
        raise ValueError("operation name must be non-empty")

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        setattr(fn, _OPERATION_ATTR, name)
        return fn

    return decorator


def _entity_decorator(kind: str, name: str, capabilities: list[str] | None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    if not name.strip():
        raise ValueError("name must be non-empty")

    capability_list = list(capabilities or [])

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        setattr(
            fn,
            _ENTITY_ATTR,
            {
                "kind": kind,
                "display_name": name,
                "capability_purpose": capability_list,
            },
        )
        if capability_list and not hasattr(fn, _OPERATION_ATTR):
            setattr(fn, _OPERATION_ATTR, capability_list[0])
        return fn

    return decorator


def fp_agent(*, name: str, capabilities: list[str] | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    return _entity_decorator("agent", name=name, capabilities=capabilities)


def fp_tool(*, name: str, capabilities: list[str] | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    return _entity_decorator("tool", name=name, capabilities=capabilities)


def fp_service(*, name: str, capabilities: list[str] | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    return _entity_decorator("service", name=name, capabilities=capabilities)


def collect_operations(scope: Mapping[str, Any]) -> dict[str, Callable[..., Any]]:
    operations: dict[str, Callable[..., Any]] = {}
    for value in scope.values():
        if not callable(value):
            continue
        operation_name = getattr(value, _OPERATION_ATTR, None)
        if not isinstance(operation_name, str):
            continue
        operations[operation_name] = value
    return operations


__all__ = [
    "collect_operations",
    "fp_agent",
    "fp_operation",
    "fp_service",
    "fp_tool",
]
