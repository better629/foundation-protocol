"""Minimal HTTP publisher for exposing FPServer over JSON-RPC + well-known card."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any
from uuid import uuid4

from fp.federation import FPServerCard
from fp.transport.http_jsonrpc import JSONRPCDispatcher


class FPHTTPPublishedServer:
    """Context-managed HTTP publisher for a local FPServer instance."""

    def __init__(
        self,
        server: Any,
        *,
        publish_entity_id: str,
        host: str = "127.0.0.1",
        port: int = 0,
        rpc_path: str = "/rpc",
        well_known_path: str = "/.well-known/fp-server.json",
        capabilities: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._server = server
        self._publish_entity_id = publish_entity_id
        self._host = host
        self._port = port
        self._rpc_path = rpc_path
        self._well_known_path = well_known_path
        self._capabilities = capabilities or {}
        self._metadata = metadata or {}

        self._httpd: ThreadingHTTPServer | None = None
        self._thread: Thread | None = None
        self._dispatcher = JSONRPCDispatcher.from_server(server)
        self._card: FPServerCard | None = None

    @property
    def server_card(self) -> FPServerCard:
        if self._card is None:
            raise RuntimeError("publisher not started")
        return self._card

    @property
    def rpc_url(self) -> str:
        return self.server_card.rpc_url

    @property
    def well_known_url(self) -> str:
        return self.server_card.well_known_url

    def start(self) -> "FPHTTPPublishedServer":
        if self._httpd is not None:
            return self

        rpc_path = self._rpc_path
        well_known_path = self._well_known_path
        dispatcher = self._dispatcher
        outer = self

        class _Handler(BaseHTTPRequestHandler):
            def _write_json(self, status: int, payload: dict[str, Any]) -> None:
                raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self) -> None:  # noqa: N802
                if self.path != well_known_path:
                    self.send_response(404)
                    self.end_headers()
                    return
                self._write_json(200, outer.server_card.to_dict())

            def do_POST(self) -> None:  # noqa: N802
                if self.path != rpc_path:
                    self.send_response(404)
                    self.end_headers()
                    return
                content_length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(content_length)
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    self._write_json(400, {"error": "invalid_json"})
                    return

                response = dispatcher.handle(payload)
                if response is None:
                    self.send_response(204)
                    self.end_headers()
                    return
                self._write_json(200, response)

            def log_message(self, fmt: str, *args: object) -> None:
                _ = (fmt, args)
                return

        self._httpd = ThreadingHTTPServer((self._host, self._port), _Handler)
        host, actual_port = self._httpd.server_address
        self._card = FPServerCard(
            card_id=f"card-{uuid4().hex}",
            entity_id=self._publish_entity_id,
            fp_version=self._server.fp_version,
            rpc_url=f"http://{host}:{actual_port}{self._rpc_path}",
            well_known_url=f"http://{host}:{actual_port}{self._well_known_path}",
            capabilities=dict(self._capabilities),
            metadata=dict(self._metadata),
        )
        self._thread = Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._httpd is None:
            return
        self._httpd.shutdown()
        self._httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
        self._thread = None
        self._httpd = None

    def __enter__(self) -> "FPHTTPPublishedServer":
        return self.start()

    def __exit__(self, exc_type, exc, tb) -> None:
        _ = (exc_type, exc, tb)
        self.stop()
