"""FP error codes and exception types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FPErrorCode(str, Enum):
    """Canonical FP semantic error codes."""

    VERSION_UNSUPPORTED = "FP_VERSION_UNSUPPORTED"
    AUTH_REQUIRED = "FP_AUTH_REQUIRED"
    AUTHZ_DENIED = "FP_AUTHZ_DENIED"
    POLICY_DENIED = "FP_POLICY_DENIED"
    INVALID_STATE_TRANSITION = "FP_INVALID_STATE_TRANSITION"
    NOT_FOUND = "FP_NOT_FOUND"
    RATE_LIMITED = "FP_RATE_LIMITED"
    BACKPRESSURE = "FP_BACKPRESSURE"
    EXTENSION_REQUIRED = "FP_EXTENSION_REQUIRED"
    INTERNAL_ERROR = "FP_INTERNAL_ERROR"
    INVALID_ARGUMENT = "FP_INVALID_ARGUMENT"
    CONFLICT = "FP_CONFLICT"
    ALREADY_EXISTS = "FP_ALREADY_EXISTS"


_DEFAULT_MESSAGES: dict[FPErrorCode, str] = {
    FPErrorCode.VERSION_UNSUPPORTED: "Unsupported FP protocol version",
    FPErrorCode.AUTH_REQUIRED: "Authentication is required",
    FPErrorCode.AUTHZ_DENIED: "Authorization denied",
    FPErrorCode.POLICY_DENIED: "Request denied by policy",
    FPErrorCode.INVALID_STATE_TRANSITION: "Invalid state transition",
    FPErrorCode.NOT_FOUND: "Requested object was not found",
    FPErrorCode.RATE_LIMITED: "Rate limit exceeded",
    FPErrorCode.BACKPRESSURE: "Backpressure threshold exceeded",
    FPErrorCode.EXTENSION_REQUIRED: "Required extension is missing",
    FPErrorCode.INTERNAL_ERROR: "Internal FP runtime error",
    FPErrorCode.INVALID_ARGUMENT: "Invalid argument",
    FPErrorCode.CONFLICT: "Conflict with current object state",
    FPErrorCode.ALREADY_EXISTS: "Object already exists",
}


@dataclass(slots=True)
class FPError(Exception):
    """Structured FP error that is safe for protocol transport."""

    code: FPErrorCode
    message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    retryable: bool = False

    def __post_init__(self) -> None:
        if self.message is None:
            self.message = _DEFAULT_MESSAGES[self.code]

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code.value,
            "message": self.message,
            "retryable": self.retryable,
        }
        if self.details:
            payload["details"] = self.details
        return payload

    def __str__(self) -> str:
        return f"{self.code.value}: {self.message}"


def not_found(kind: str, object_id: str) -> FPError:
    return FPError(
        code=FPErrorCode.NOT_FOUND,
        details={"kind": kind, "id": object_id},
    )
