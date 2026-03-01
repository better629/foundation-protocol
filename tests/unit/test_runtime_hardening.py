from __future__ import annotations

import unittest

from fp.app import FPServer, make_default_entity
from fp.protocol import EntityKind, FPError, FPErrorCode
from fp.runtime.backpressure import BackpressureController


class RuntimeHardeningTests(unittest.TestCase):
    def test_backpressure_windows_are_isolated_per_stream(self) -> None:
        controller = BackpressureController(default_window=10)
        controller.configure_stream("stream-a", window=1)
        controller.configure_stream("stream-b", window=3)

        with self.assertRaises(FPError) as exc:
            controller.on_deliver("stream-a", 2)
        self.assertIs(exc.exception.code, FPErrorCode.BACKPRESSURE)

        controller.on_deliver("stream-b", 2)
        self.assertEqual(controller.outstanding("stream-b"), 2)

    def test_push_config_requires_url_scope_and_event_types(self) -> None:
        server = FPServer()
        server.register_entity(make_default_entity("fp:agent:a", EntityKind.AGENT))
        server.register_entity(make_default_entity("fp:agent:b", EntityKind.AGENT))
        session = server.sessions_create(
            participants={"fp:agent:a", "fp:agent:b"},
            roles={"fp:agent:a": {"producer"}, "fp:agent:b": {"consumer"}},
        )

        with self.assertRaises(FPError) as exc:
            server.push_config_set(
                {
                    "push_config_id": "pcfg-1",
                    "url": "https://hooks.example/fp",
                    "scope": {"session_id": session.session_id},
                }
            )
        self.assertIs(exc.exception.code, FPErrorCode.INVALID_ARGUMENT)


if __name__ == "__main__":
    unittest.main()
