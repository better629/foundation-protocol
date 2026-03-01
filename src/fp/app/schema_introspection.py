"""Typed operation schema extraction and lightweight payload validation."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from types import UnionType
from typing import Any, Callable, Literal, Union, get_args, get_origin, get_type_hints

from fp.protocol import FPError, FPErrorCode

_NONE_TYPE = type(None)


@dataclass(slots=True)
class OperationContract:
    operation: str
    schema: dict[str, Any]
    invoke: Callable[[Any, dict[str, Any]], Any]


@dataclass(slots=True)
class _ParameterSpec:
    name: str
    annotation: Any
    required: bool
    default: Any
    schema: dict[str, Any]


def build_operation_contract(operation: str, fn: Callable[..., Any]) -> OperationContract:
    signature = inspect.signature(fn)
    type_hints = get_type_hints(fn, include_extras=True)
    parameters = list(signature.parameters.values())

    accepts_context = False
    if parameters and parameters[0].name in {"ctx", "context"}:
        accepts_context = True
        parameters = parameters[1:]

    if _is_payload_style_signature(parameters, type_hints=type_hints):
        schema = {"type": "object", "additionalProperties": True}

        def invoke(context: Any, payload: dict[str, Any]) -> Any:
            _ = context
            if not isinstance(payload, dict):
                raise FPError(FPErrorCode.INVALID_ARGUMENT, "input payload must be an object")
            return fn(payload)

        return OperationContract(operation=operation, schema=schema, invoke=invoke)

    specs: list[_ParameterSpec] = []
    properties: dict[str, dict[str, Any]] = {}
    required: list[str] = []
    for parameter in parameters:
        if parameter.kind in {inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD}:
            raise TypeError(f"operation {operation} does not support *args/**kwargs")
        annotation = type_hints.get(
            parameter.name,
            parameter.annotation if parameter.annotation is not inspect._empty else Any,
        )
        item_schema = _annotation_to_schema(annotation)
        is_required = parameter.default is inspect._empty
        default = parameter.default if not is_required else None
        specs.append(
            _ParameterSpec(
                name=parameter.name,
                annotation=annotation,
                required=is_required,
                default=default,
                schema=item_schema,
            )
        )
        properties[parameter.name] = item_schema
        if is_required:
            required.append(parameter.name)

    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required

    def invoke(context: Any, payload: dict[str, Any]) -> Any:
        if not isinstance(payload, dict):
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "input payload must be an object")

        known = {spec.name for spec in specs}
        unknown = sorted(set(payload.keys()) - known)
        if unknown:
            raise FPError(
                FPErrorCode.INVALID_ARGUMENT,
                message="unexpected input fields",
                details={"unexpected_fields": unknown},
            )

        kwargs: dict[str, Any] = {}
        for spec in specs:
            if spec.name not in payload:
                if spec.required:
                    raise FPError(
                        FPErrorCode.INVALID_ARGUMENT,
                        message=f"missing required parameter: {spec.name}",
                        details={"parameter": spec.name},
                    )
                kwargs[spec.name] = spec.default
                continue
            value = payload[spec.name]
            if not _matches_annotation(value, spec.annotation):
                raise FPError(
                    FPErrorCode.INVALID_ARGUMENT,
                    message=f"parameter '{spec.name}' expected {_annotation_name(spec.annotation)}",
                    details={
                        "parameter": spec.name,
                        "expected": _annotation_name(spec.annotation),
                        "received_type": type(value).__name__,
                    },
                )
            kwargs[spec.name] = value

        if accepts_context:
            return fn(context, **kwargs)
        return fn(**kwargs)

    return OperationContract(operation=operation, schema=schema, invoke=invoke)


def _is_payload_style_signature(parameters: list[inspect.Parameter], *, type_hints: dict[str, Any]) -> bool:
    if len(parameters) != 1:
        return False
    parameter = parameters[0]
    if parameter.name not in {"payload", "input_payload"}:
        return False
    annotation = type_hints.get(parameter.name, parameter.annotation)
    if annotation is inspect._empty or annotation is Any:
        return True
    origin = get_origin(annotation)
    return annotation is dict or origin is dict


def _annotation_to_schema(annotation: Any) -> dict[str, Any]:
    if annotation is inspect._empty or annotation is Any:
        return {}

    optional, inner = _optional_inner(annotation)
    if optional:
        inner_schema = _annotation_to_schema(inner)
        if not inner_schema:
            return {}
        return {"anyOf": [inner_schema, {"type": "null"}]}

    origin = get_origin(annotation)
    if origin in {list, tuple, set}:
        args = get_args(annotation)
        item_schema = _annotation_to_schema(args[0]) if args else {}
        return {"type": "array", "items": item_schema}
    if origin is dict:
        args = get_args(annotation)
        value_schema = _annotation_to_schema(args[1]) if len(args) == 2 else {}
        schema: dict[str, Any] = {"type": "object"}
        if value_schema:
            schema["additionalProperties"] = value_schema
        return schema
    if origin in {Union, UnionType}:
        return {"anyOf": [_annotation_to_schema(item) for item in get_args(annotation)]}
    if origin is Literal:
        return {"enum": list(get_args(annotation))}

    primitive_map: dict[Any, str] = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
    }
    primitive = primitive_map.get(annotation)
    if primitive is not None:
        return {"type": primitive}

    if isinstance(annotation, type):
        return {"type": "object"}
    return {}


def _matches_annotation(value: Any, annotation: Any) -> bool:
    if annotation is inspect._empty or annotation is Any:
        return True

    optional, inner = _optional_inner(annotation)
    if optional:
        return value is None or _matches_annotation(value, inner)

    origin = get_origin(annotation)
    if origin in {Union, UnionType}:
        return any(_matches_annotation(value, item) for item in get_args(annotation))
    if origin is Literal:
        return value in set(get_args(annotation))
    if origin in {list, tuple, set}:
        if not isinstance(value, list):
            return False
        args = get_args(annotation)
        if not args:
            return True
        return all(_matches_annotation(item, args[0]) for item in value)
    if origin is dict:
        if not isinstance(value, dict):
            return False
        args = get_args(annotation)
        if len(args) != 2:
            return True
        key_type, value_type = args
        return all(_matches_annotation(k, key_type) and _matches_annotation(v, value_type) for k, v in value.items())

    if annotation is bool:
        return isinstance(value, bool)
    if annotation is int:
        return isinstance(value, int) and not isinstance(value, bool)
    if annotation is float:
        return (isinstance(value, float) or isinstance(value, int)) and not isinstance(value, bool)
    if annotation is str:
        return isinstance(value, str)
    if annotation is dict:
        return isinstance(value, dict)
    if annotation is list:
        return isinstance(value, list)
    if annotation is tuple:
        return isinstance(value, tuple)
    if annotation is set:
        return isinstance(value, set)

    if isinstance(annotation, type):
        return isinstance(value, annotation)
    return True


def _optional_inner(annotation: Any) -> tuple[bool, Any]:
    origin = get_origin(annotation)
    if origin not in {Union, UnionType}:
        return False, annotation
    args = list(get_args(annotation))
    if _NONE_TYPE not in args:
        return False, annotation
    non_none = [item for item in args if item is not _NONE_TYPE]
    if len(non_none) == 1:
        return True, non_none[0]
    return False, annotation


def _annotation_name(annotation: Any) -> str:
    optional, inner = _optional_inner(annotation)
    if optional:
        return f"{_annotation_name(inner)} | None"
    origin = get_origin(annotation)
    if origin in {Union, UnionType}:
        return " | ".join(_annotation_name(item) for item in get_args(annotation))
    if origin is Literal:
        values = ", ".join(repr(item) for item in get_args(annotation))
        return f"Literal[{values}]"
    if origin in {list, tuple, set, dict}:
        return str(annotation)
    if annotation is Any:
        return "Any"
    if isinstance(annotation, type):
        return annotation.__name__
    return str(annotation)


__all__ = ["OperationContract", "build_operation_contract"]
