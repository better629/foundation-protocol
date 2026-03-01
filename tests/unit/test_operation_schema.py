from __future__ import annotations

import unittest

from fp.app.decorators import operation
from fp.protocol import FPError, FPErrorCode
from fp.runtime.dispatch_engine import DispatchContext


@operation("math.add")
def add(x: int, y: int, scale: float = 1.0) -> dict:
    return {"total": (x + y) * scale}


@operation("ctx.echo")
def echo_with_ctx(ctx: DispatchContext, text: str) -> dict:
    return {"activity_id": ctx.activity_id, "text": text}


class OperationSchemaTests(unittest.TestCase):
    def test_decorator_exposes_schema_and_metadata(self) -> None:
        self.assertEqual(getattr(add, "__fp_operation__"), "math.add")
        schema = getattr(add, "__fp_schema__")
        self.assertEqual(schema["type"], "object")
        self.assertEqual(set(schema["required"]), {"x", "y"})
        self.assertEqual(schema["properties"]["x"]["type"], "integer")
        self.assertEqual(schema["properties"]["scale"]["type"], "number")

    def test_generated_invoker_validates_parameters(self) -> None:
        invoke = getattr(add, "__fp_invoke__")
        ctx = DispatchContext(
            session_id="sess-1",
            activity_id="act-1",
            operation="math.add",
            actor_entity_id="fp:agent:a",
        )

        self.assertEqual(invoke(ctx, {"x": 2, "y": 3}), {"total": 5.0})

        with self.assertRaises(FPError) as exc:
            invoke(ctx, {"x": "2", "y": 3})
        self.assertIs(exc.exception.code, FPErrorCode.INVALID_ARGUMENT)

        with self.assertRaises(FPError) as missing:
            invoke(ctx, {"x": 2})
        self.assertIs(missing.exception.code, FPErrorCode.INVALID_ARGUMENT)

    def test_context_aware_operation_receives_dispatch_context(self) -> None:
        invoke = getattr(echo_with_ctx, "__fp_invoke__")
        ctx = DispatchContext(
            session_id="sess-7",
            activity_id="act-9",
            operation="ctx.echo",
            actor_entity_id="fp:agent:b",
        )
        result = invoke(ctx, {"text": "hello"})
        self.assertEqual(result, {"activity_id": "act-9", "text": "hello"})


if __name__ == "__main__":
    unittest.main()
