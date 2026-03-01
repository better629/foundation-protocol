"""Simple middleware pipeline primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


Handler = Callable[[dict[str, Any]], dict[str, Any]]
Middleware = Callable[[dict[str, Any], Handler], dict[str, Any]]


@dataclass(slots=True)
class MiddlewarePipeline:
    middlewares: list[Middleware]

    def run(self, payload: dict[str, Any], terminal: Handler) -> dict[str, Any]:
        handler = terminal
        for middleware in reversed(self.middlewares):
            next_handler = handler

            def wrapped(data: dict[str, Any], mw=middleware, nxt=next_handler) -> dict[str, Any]:
                return mw(data, nxt)

            handler = wrapped
        return handler(payload)
