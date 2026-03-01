from __future__ import annotations

import unittest

from fp.app import FPClient


class _RecorderTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def call(self, method: str, params: dict | None = None):
        payload = dict(params or {})
        self.calls.append((method, payload))
        if method == "fp/ping":
            return {"ok": True, "fp_version": "0.1.0"}
        if method == "fp/sessions.create":
            return {"session_id": "sess-1"}
        return {"ok": True}


class ClientSinglePathTests(unittest.TestCase):
    def test_client_requires_transport(self) -> None:
        with self.assertRaises(TypeError):
            FPClient()  # type: ignore[call-arg]

    def test_public_calls_flow_through_transport(self) -> None:
        transport = _RecorderTransport()
        client = FPClient(transport=transport)

        ping = client.ping()
        created = client.session_create(
            participants={"fp:agent:a", "fp:agent:b"},
            roles={"fp:agent:a": {"a"}, "fp:agent:b": {"b"}},
        )

        self.assertEqual(ping["ok"], True)
        self.assertEqual(created["session_id"], "sess-1")
        self.assertEqual(transport.calls[0][0], "fp/ping")
        self.assertEqual(transport.calls[1][0], "fp/sessions.create")


if __name__ == "__main__":
    unittest.main()
