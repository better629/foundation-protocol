"""HTTP JSON-RPC client transport."""

from __future__ import annotations

import json
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from fp.protocol import FPError, FPErrorCode


class HTTPJSONRPCClientTransport:
    def __init__(
        self,
        rpc_url: str,
        *,
        timeout_seconds: float = 10.0,
        headers: dict[str, str] | None = None,
        ssl_context: ssl.SSLContext | None = None,
    ) -> None:
        if not rpc_url:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "rpc_url must be non-empty")
        self._rpc_url = rpc_url
        self._timeout = timeout_seconds
        self._headers = {"Content-Type": "application/json", **(headers or {})}
        self._ssl_context = ssl_context

    def call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "id": f"req-{uuid4().hex}",
            "method": method,
            "params": params or {},
        }
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request = Request(self._rpc_url, data=raw, headers=self._headers, method="POST")
        try:
            with urlopen(request, timeout=self._timeout, context=self._ssl_context) as response:
                response_body = response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise FPError(
                FPErrorCode.INTERNAL_ERROR,
                message="remote FP server returned HTTP error",
                details={"status": exc.code, "url": self._rpc_url, "detail": detail},
            ) from exc
        except URLError as exc:
            raise FPError(
                FPErrorCode.INTERNAL_ERROR,
                message="failed to reach remote FP server",
                details={"url": self._rpc_url, "detail": str(exc.reason)},
                retryable=True,
            ) from exc
        except ssl.SSLError as exc:
            raise FPError(
                FPErrorCode.INTERNAL_ERROR,
                message="TLS handshake failed",
                details={"url": self._rpc_url, "detail": str(exc)},
                retryable=True,
            ) from exc

        if not response_body:
            return None
        try:
            decoded = json.loads(response_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise FPError(FPErrorCode.INTERNAL_ERROR, "remote FP server returned non-JSON response") from exc
        if not isinstance(decoded, dict):
            raise FPError(FPErrorCode.INTERNAL_ERROR, "remote FP server returned malformed response")
        error = decoded.get("error")
        if isinstance(error, dict):
            raise _map_jsonrpc_error(error)
        return decoded.get("result")


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
        message=error_payload.get("message", "remote call failed"),
        details={"remote_error": error_payload},
    )
