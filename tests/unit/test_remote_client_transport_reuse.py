from __future__ import annotations

import unittest

from fp.federation.network import RemoteFPClient
from fp.transport.client_http_jsonrpc import HTTPJSONRPCClientTransport


class _FakeTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def call(self, method: str, params: dict | None = None):
        payload = dict(params or {})
        self.calls.append((method, payload))
        return {"ok": True}


class RemoteClientTransportReuseTests(unittest.TestCase):
    def test_remote_client_composes_http_transport(self) -> None:
        client = RemoteFPClient("http://127.0.0.1:9999/rpc")
        self.assertIsInstance(client._transport, HTTPJSONRPCClientTransport)  # type: ignore[attr-defined]

    def test_remote_client_call_delegates_to_transport(self) -> None:
        client = RemoteFPClient("http://127.0.0.1:9999/rpc")
        fake = _FakeTransport()
        client._transport = fake  # type: ignore[attr-defined]
        out = client.call("fp/ping", {"x": 1})
        self.assertEqual(out, {"ok": True})
        self.assertEqual(fake.calls, [("fp/ping", {"x": 1})])


if __name__ == "__main__":
    unittest.main()
