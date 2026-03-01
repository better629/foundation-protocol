from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from fp.federation import DirectoryService, FPServerCard
from fp.protocol import FPError, FPErrorCode


class _Clock:
    def __init__(self) -> None:
        self._now = datetime(2026, 3, 1, 0, 0, 0, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self._now

    def advance(self, *, seconds: int) -> None:
        self._now = self._now + timedelta(seconds=seconds)


class DirectoryTTLHealthACLTests(unittest.TestCase):
    def test_directory_enforces_acl_health_and_ttl_with_heartbeat_refresh(self) -> None:
        clock = _Clock()
        directory = DirectoryService(now_fn=clock.now)
        issued_at = clock.now().isoformat().replace("+00:00", "Z")
        expires_at = (clock.now() + timedelta(seconds=30)).isoformat().replace("+00:00", "Z")
        card = FPServerCard(
            card_id="card-1",
            entity_id="fp:agent:directory-node",
            fp_version="0.1.0",
            rpc_url="https://node.example/rpc",
            well_known_url="https://node.example/.well-known/fp-server.json",
            metadata={
                "acl_publish": ["fp:agent:owner"],
                "acl_read": ["fp:agent:reader"],
            },
            sign_alg="none",
            key_ref="fp:agent:directory-node#local",
            signature="unsigned",
            issued_at=issued_at,
            expires_at=expires_at,
            ttl_seconds=30,
        )

        with self.assertRaises(FPError) as denied_publish:
            directory.publish(card, actor_ref="fp:agent:intruder")
        self.assertIs(denied_publish.exception.code, FPErrorCode.AUTHZ_DENIED)

        directory.publish(card, actor_ref="fp:agent:owner")
        with self.assertRaises(FPError) as denied_read:
            directory.resolve("fp:agent:directory-node", actor_ref="fp:agent:intruder")
        self.assertIs(denied_read.exception.code, FPErrorCode.AUTHZ_DENIED)

        resolved = directory.resolve("fp:agent:directory-node", actor_ref="fp:agent:reader")
        self.assertEqual(resolved.entity_id, "fp:agent:directory-node")

        clock.advance(seconds=20)
        directory.heartbeat("fp:agent:directory-node", actor_ref="fp:agent:owner")
        clock.advance(seconds=20)
        refreshed = directory.resolve("fp:agent:directory-node", actor_ref="fp:agent:reader")
        self.assertEqual(refreshed.entity_id, "fp:agent:directory-node")

        directory.set_health("fp:agent:directory-node", healthy=False, reason="probe-timeout")
        with self.assertRaises(FPError) as unhealthy:
            directory.resolve("fp:agent:directory-node", actor_ref="fp:agent:reader", require_healthy=True)
        self.assertIs(unhealthy.exception.code, FPErrorCode.NOT_FOUND)

        directory.set_health("fp:agent:directory-node", healthy=True, reason=None)
        clock.advance(seconds=40)
        with self.assertRaises(FPError) as expired:
            directory.resolve("fp:agent:directory-node", actor_ref="fp:agent:reader")
        self.assertIs(expired.exception.code, FPErrorCode.NOT_FOUND)


if __name__ == "__main__":
    unittest.main()
