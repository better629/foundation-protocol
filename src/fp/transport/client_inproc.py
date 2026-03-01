"""In-process JSON-RPC client transport."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fp.protocol import FPError, FPErrorCode
from fp.transport.http_jsonrpc import JSONRPCDispatcher


class InProcessJSONRPCClientTransport:
    def __init__(self, server: Any) -> None:
        self._dispatcher = JSONRPCDispatcher.from_server(server)

    def call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "id": f"req-{uuid4().hex}",
            "method": method,
            "params": params or {},
        }
        response = self._dispatcher.handle(payload)
        if response is None:
            return None
        error = response.get("error")
        if isinstance(error, dict):
            raise _map_jsonrpc_error(error)
        return response.get("result")


def _map_jsonrpc_error(error_payload: dict[str, Any]) -> FPError:
    data = error_payload.get("data")
    if isinstance(data, dict):
        fp = data.get("fp")
        if isinstance(fp, dict):
            code = fp.get("code")
            if isinstance(code, str) and code in {item.value for item in FPErrorCode}:
                return FPError(
                    code=FPErrorCode(code),
                    message=fp.get("message"),
                    details=dict(fp.get("details", {})),
                    retryable=bool(fp.get("retryable", False)),
                )
    return FPError(
        FPErrorCode.INTERNAL_ERROR,
        message=error_payload.get("message", "in-process transport call failed"),
        details={"remote_error": error_payload},
    )
