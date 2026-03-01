from __future__ import annotations

import unittest
from unittest.mock import patch
from urllib.error import URLError

from fp.app import FPServer
from fp.federation import RemoteFPClient, fetch_server_card
from fp.transport import FPHTTPPublishedServer
from fp.transport.reliability import RetryPolicy


class RemoteRetryRecoveryTests(unittest.TestCase):
    def test_remote_client_recovers_after_one_transient_failure(self) -> None:
        server = FPServer(server_entity_id="fp:system:retry")
        with FPHTTPPublishedServer(server, publish_entity_id="fp:agent:server", host="127.0.0.1", port=0) as published:
            card = fetch_server_card(published.well_known_url)
            client = RemoteFPClient(
                card.rpc_url,
                retry_policy=RetryPolicy(max_attempts=2, backoff_initial_seconds=0.0, jitter_ratio=0.0),
                keep_alive=False,
            )

            original_urlopen = __import__("fp.transport.client_http_jsonrpc", fromlist=["urlopen"]).urlopen
            calls = {"count": 0}

            def flaky_urlopen(*args, **kwargs):
                calls["count"] += 1
                if calls["count"] == 1:
                    raise URLError("temporary")
                return original_urlopen(*args, **kwargs)

            with patch("fp.transport.client_http_jsonrpc.urlopen", side_effect=flaky_urlopen):
                ping = client.call("fp/ping", {})

            self.assertEqual(ping["ok"], True)
            self.assertEqual(calls["count"], 2)


if __name__ == "__main__":
    unittest.main()
