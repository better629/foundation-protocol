"""Decorator helpers for application wiring."""

from __future__ import annotations

from typing import Callable


def operation(name: str):
    def decorator(fn: Callable):
        setattr(fn, "__fp_operation__", name)
        return fn

    return decorator
