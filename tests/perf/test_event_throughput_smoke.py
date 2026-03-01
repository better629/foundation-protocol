from __future__ import annotations

import time
import unittest

from fp.app import FPServer, make_default_entity
from fp.protocol import EntityKind


class EventThroughputSmokeTests(unittest.TestCase):
    def test_event_throughput_smoke(self) -> None:
        server = FPServer()
        server.register_entity(make_default_entity("fp:agent:a", EntityKind.AGENT))
        server.register_entity(make_default_entity("fp:agent:b", EntityKind.AGENT))
        session = server.sessions_create(
            participants={"fp:agent:a", "fp:agent:b"},
            roles={"fp:agent:a": {"producer"}, "fp:agent:b": {"consumer"}},
        )

        start = time.perf_counter()
        for i in range(200):
            server.emit_event(
                event_type="perf.tick",
                session_id=session.session_id,
                producer_entity_id="fp:agent:a",
                payload={"i": i},
            )
        elapsed = time.perf_counter() - start

        self.assertLess(elapsed, 1.0)


if __name__ == "__main__":
    unittest.main()
