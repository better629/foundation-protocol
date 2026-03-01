"""Minimal HTTP publisher for exposing FPServer over JSON-RPC + well-known card."""

from __future__ import annotations

import json
import ssl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any
from uuid import uuid4

from fp.federation import FPServerCard, new_unsigned_server_card_fields
from fp.security.auth import Authenticator, extract_bearer_token
from fp.security.mtls import MTLSConfig, create_server_ssl_context
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
        card_ttl_seconds: int = 600,
        authenticator: Authenticator | None = None,
        ssl_context: ssl.SSLContext | None = None,
        mtls: MTLSConfig | None = None,
    ) -> None:
        if ssl_context is not None and mtls is not None:
            raise ValueError("ssl_context and mtls are mutually exclusive")
        self._server = server
        self._publish_entity_id = publish_entity_id
        self._host = host
        self._port = port
        self._rpc_path = rpc_path
        self._well_known_path = well_known_path
        self._capabilities = capabilities or {}
        self._metadata = metadata or {}
        self._card_ttl_seconds = card_ttl_seconds
        self._authenticator = authenticator
        self._ssl_context = ssl_context
        self._mtls = mtls

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
                if outer._authenticator is not None:
                    credentials = extract_bearer_token(self.headers.get("Authorization"))
                    principal = outer._authenticator.authenticate(credentials)
                    if principal is None:
                        self._write_json(401, {"error": "unauthorized"})
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
        tls_context = self._ssl_context
        if tls_context is None and self._mtls is not None:
            tls_context = create_server_ssl_context(self._mtls)
        if tls_context is not None:
            self._httpd.socket = tls_context.wrap_socket(self._httpd.socket, server_side=True)
        host, actual_port = self._httpd.server_address
        scheme = "https" if tls_context is not None else "http"
        issued_at, expires_at, ttl_seconds = new_unsigned_server_card_fields(self._card_ttl_seconds)
        self._card = FPServerCard(
            card_id=f"card-{uuid4().hex}",
            entity_id=self._publish_entity_id,
            fp_version=self._server.fp_version,
            rpc_url=f"{scheme}://{host}:{actual_port}{self._rpc_path}",
            well_known_url=f"{scheme}://{host}:{actual_port}{self._well_known_path}",
            capabilities=dict(self._capabilities),
            metadata=dict(self._metadata),
            sign_alg="none",
            key_ref=f"{self._publish_entity_id}#local",
            signature="unsigned",
            issued_at=issued_at,
            expires_at=expires_at,
            ttl_seconds=ttl_seconds,
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
