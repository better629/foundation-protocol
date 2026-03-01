"""Decorator helpers for application wiring."""

from __future__ import annotations

from typing import Any, Callable

from .schema_introspection import build_operation_contract


def operation(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        contract = build_operation_contract(name, fn)
        setattr(fn, "__fp_operation__", name)
        setattr(fn, "__fp_schema__", contract.schema)
        setattr(fn, "__fp_invoke__", contract.invoke)
        return fn

    return decorator
