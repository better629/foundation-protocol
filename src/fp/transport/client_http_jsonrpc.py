"""HTTP JSON-RPC client transport."""

from __future__ import annotations

import http.client
import json
import ssl
import time
from dataclasses import dataclass
from threading import RLock
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import SplitResult, urlsplit
from urllib.request import Request, urlopen
from uuid import uuid4

from fp.protocol import FPError, FPErrorCode
from fp.transport.reliability import CircuitBreaker, RetryPolicy


@dataclass(slots=True)
class _HTTPStatusError(Exception):
    status: int
    detail: str


class _KeepAliveConnection:
    def __init__(self, rpc_url: str, *, timeout_seconds: float, ssl_context: ssl.SSLContext | None) -> None:
        parsed = urlsplit(rpc_url)
        if parsed.scheme not in {"http", "https"}:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "rpc_url scheme must be http or https")
        if not parsed.hostname:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "rpc_url must include hostname")

        self._parsed = parsed
        self._timeout = timeout_seconds
        self._ssl_context = ssl_context
        self._lock = RLock()
        self._connection: http.client.HTTPConnection | http.client.HTTPSConnection | None = None

    def post(self, *, body: bytes, headers: dict[str, str]) -> bytes:
        with self._lock:
            for attempt in range(2):
                connection = self._ensure_connection()
                try:
                    connection.request("POST", self._target_path(), body=body, headers=headers)
                    response = connection.getresponse()
                    payload = response.read()
                except (http.client.HTTPException, OSError) as exc:
                    self._drop_connection()
                    if attempt == 0:
                        continue
                    raise URLError(str(exc)) from exc

                if int(response.status) >= 400:
                    detail = payload.decode("utf-8", errors="replace")
                    raise _HTTPStatusError(status=int(response.status), detail=detail)
                return payload

        return b""

    def close(self) -> None:
        with self._lock:
            self._drop_connection()

    def _target_path(self) -> str:
        path = self._parsed.path or "/"
        if self._parsed.query:
            return f"{path}?{self._parsed.query}"
        return path

    def _ensure_connection(self) -> http.client.HTTPConnection | http.client.HTTPSConnection:
        if self._connection is not None:
            return self._connection

        host = self._parsed.hostname or ""
        if self._parsed.scheme == "https":
            self._connection = http.client.HTTPSConnection(
                host,
                self._parsed.port or 443,
                timeout=self._timeout,
                context=self._ssl_context,
            )
        else:
            self._connection = http.client.HTTPConnection(
                host,
                self._parsed.port or 80,
                timeout=self._timeout,
            )
        return self._connection

    def _drop_connection(self) -> None:
        if self._connection is None:
            return
        try:
            self._connection.close()
        finally:
            self._connection = None


class HTTPJSONRPCClientTransport:
    def __init__(
        self,
        rpc_url: str,
        *,
        timeout_seconds: float = 10.0,
        headers: dict[str, str] | None = None,
        ssl_context: ssl.SSLContext | None = None,
        retry_policy: RetryPolicy | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        keep_alive: bool = True,
    ) -> None:
        if not rpc_url:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "rpc_url must be non-empty")
        self._rpc_url = rpc_url
        self._timeout = timeout_seconds
        self._headers = {
            "Content-Type": "application/json",
            "Connection": "keep-alive" if keep_alive else "close",
            **(headers or {}),
        }
        self._ssl_context = ssl_context
        self._retry_policy = retry_policy or RetryPolicy()
        self._circuit_breaker = circuit_breaker
        self._parsed_url: SplitResult = urlsplit(rpc_url)
        self._keep_alive = keep_alive
        self._keep_alive_conn = (
            _KeepAliveConnection(rpc_url, timeout_seconds=timeout_seconds, ssl_context=ssl_context)
            if keep_alive and self._parsed_url.scheme in {"http", "https"}
            else None
        )

    def call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        if self._circuit_breaker is not None:
            self._circuit_breaker.before_call()

        attempt = 0
        last_error: FPError | None = None
        while attempt < self._retry_policy.max_attempts:
            attempt += 1
            payload = {
                "jsonrpc": "2.0",
                "id": f"req-{uuid4().hex}",
                "method": method,
                "params": params or {},
            }
            raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            try:
                response_body = self._post(raw)
            except _HTTPStatusError as exc:
                retryable = exc.status in self._retry_policy.retryable_http_status
                last_error = FPError(
                    FPErrorCode.INTERNAL_ERROR,
                    message="remote FP server returned HTTP error",
                    details={"status": exc.status, "url": self._rpc_url, "detail": exc.detail},
                    retryable=retryable,
                )
                if self._maybe_retry(attempt, retryable):
                    continue
                self._record_failure()
                raise last_error
            except HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                retryable = exc.code in self._retry_policy.retryable_http_status
                last_error = FPError(
                    FPErrorCode.INTERNAL_ERROR,
                    message="remote FP server returned HTTP error",
                    details={"status": exc.code, "url": self._rpc_url, "detail": detail},
                    retryable=retryable,
                )
                if self._maybe_retry(attempt, retryable):
                    continue
                self._record_failure()
                raise last_error from exc
            except URLError as exc:
                last_error = FPError(
                    FPErrorCode.INTERNAL_ERROR,
                    message="failed to reach remote FP server",
                    details={"url": self._rpc_url, "detail": str(exc.reason)},
                    retryable=True,
                )
                if self._maybe_retry(attempt, True):
                    continue
                self._record_failure()
                raise last_error from exc
            except ssl.SSLError as exc:
                last_error = FPError(
                    FPErrorCode.INTERNAL_ERROR,
                    message="TLS handshake failed",
                    details={"url": self._rpc_url, "detail": str(exc)},
                    retryable=True,
                )
                if self._maybe_retry(attempt, True):
                    continue
                self._record_failure()
                raise last_error from exc

            if not response_body:
                self._record_success()
                return None
            try:
                decoded = json.loads(response_body.decode("utf-8"))
            except json.JSONDecodeError as exc:
                self._record_failure()
                raise FPError(FPErrorCode.INTERNAL_ERROR, "remote FP server returned non-JSON response") from exc
            if not isinstance(decoded, dict):
                self._record_failure()
                raise FPError(FPErrorCode.INTERNAL_ERROR, "remote FP server returned malformed response")
            error = decoded.get("error")
            if isinstance(error, dict):
                fp_error = _map_jsonrpc_error(error)
                if self._maybe_retry(attempt, fp_error.retryable):
                    continue
                self._record_failure()
                raise fp_error
            self._record_success()
            return decoded.get("result")

        self._record_failure()
        raise last_error or FPError(FPErrorCode.INTERNAL_ERROR, "remote call failed")

    def close(self) -> None:
        if self._keep_alive_conn is not None:
            self._keep_alive_conn.close()

    def _post(self, body: bytes) -> bytes:
        if self._keep_alive_conn is not None:
            return self._keep_alive_conn.post(body=body, headers=self._headers)

        request = Request(self._rpc_url, data=body, headers=self._headers, method="POST")
        with urlopen(request, timeout=self._timeout, context=self._ssl_context) as response:
            return response.read()

    def _maybe_retry(self, attempt: int, retryable: bool) -> bool:
        if not retryable:
            return False
        if attempt >= self._retry_policy.max_attempts:
            return False
        delay = self._retry_policy.delay_for_attempt(attempt_index=attempt)
        if delay > 0:
            time.sleep(delay)
        return True

    def _record_success(self) -> None:
        if self._circuit_breaker is not None:
            self._circuit_breaker.record_success()

    def _record_failure(self) -> None:
        if self._circuit_breaker is not None:
            self._circuit_breaker.record_failure()


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
