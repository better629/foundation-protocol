from __future__ import annotations

import io
import json
import unittest
from unittest.mock import patch
from urllib.error import URLError

from fp.protocol import FPError, FPErrorCode
from fp.transport.client_http_jsonrpc import HTTPJSONRPCClientTransport
from fp.transport.reliability import CircuitBreaker, CircuitBreakerConfig, RetryPolicy


class _FakeHTTPResponse(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        _ = (exc_type, exc, tb)
        self.close()
        return False


class _KeepAliveHTTPResponse:
    def __init__(self, payload: bytes, status: int = 200) -> None:
        self._payload = payload
        self.status = status

    def read(self) -> bytes:
        return self._payload


class _KeepAliveConnection:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload
        self.request_calls = 0
        self.closed = False

    def request(self, method: str, path: str, body: bytes | None = None, headers: dict | None = None) -> None:
        _ = (method, path, body, headers)
        self.request_calls += 1

    def getresponse(self) -> _KeepAliveHTTPResponse:
        return _KeepAliveHTTPResponse(self._payload, status=200)

    def close(self) -> None:
        self.closed = True


class TransportRetryBreakerTests(unittest.TestCase):
    def test_retry_recovers_after_transient_network_error(self) -> None:
        payload = json.dumps({"jsonrpc": "2.0", "id": "x", "result": {"ok": True}}).encode("utf-8")
        policy = RetryPolicy(max_attempts=2, backoff_initial_seconds=0.0, jitter_ratio=0.0)
        transport = HTTPJSONRPCClientTransport("http://127.0.0.1:9999/rpc", retry_policy=policy, keep_alive=False)

        with patch(
            "fp.transport.client_http_jsonrpc.urlopen",
            side_effect=[URLError("temporary"), _FakeHTTPResponse(payload)],
        ) as mocked:
            result = transport.call("fp/ping", {})

        self.assertEqual(result["ok"], True)
        self.assertEqual(mocked.call_count, 2)

    def test_circuit_breaker_opens_after_repeated_failures(self) -> None:
        policy = RetryPolicy(max_attempts=1, backoff_initial_seconds=0.0, jitter_ratio=0.0)
        breaker = CircuitBreaker(CircuitBreakerConfig(failure_threshold=2, recovery_timeout_seconds=60.0))
        transport = HTTPJSONRPCClientTransport(
            "http://127.0.0.1:9999/rpc",
            retry_policy=policy,
            circuit_breaker=breaker,
            keep_alive=False,
        )

        with patch("fp.transport.client_http_jsonrpc.urlopen", side_effect=URLError("down")) as mocked:
            with self.assertRaises(FPError):
                transport.call("fp/ping", {})
            with self.assertRaises(FPError):
                transport.call("fp/ping", {})
            with self.assertRaises(FPError) as open_exc:
                transport.call("fp/ping", {})

        self.assertIs(open_exc.exception.code, FPErrorCode.RATE_LIMITED)
        self.assertEqual(mocked.call_count, 2)

    def test_keep_alive_reuses_single_http_connection(self) -> None:
        payload = json.dumps({"jsonrpc": "2.0", "id": "x", "result": {"ok": True}}).encode("utf-8")
        created: list[_KeepAliveConnection] = []

        def build_connection(*args, **kwargs):
            _ = (args, kwargs)
            conn = _KeepAliveConnection(payload)
            created.append(conn)
            return conn

        with patch("fp.transport.client_http_jsonrpc.http.client.HTTPConnection", side_effect=build_connection):
            transport = HTTPJSONRPCClientTransport("http://127.0.0.1:9999/rpc", keep_alive=True)
            first = transport.call("fp/ping", {})
            second = transport.call("fp/ping", {})
            transport.close()

        self.assertEqual(first["ok"], True)
        self.assertEqual(second["ok"], True)
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].request_calls, 2)
        self.assertTrue(created[0].closed)


if __name__ == "__main__":
    unittest.main()
