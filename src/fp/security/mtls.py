"""mTLS configuration helpers."""

from __future__ import annotations

import ssl
from dataclasses import dataclass


@dataclass(slots=True)
class MTLSConfig:
    certfile: str
    keyfile: str
    ca_certfile: str
    require_client_cert: bool = True


def create_server_ssl_context(config: MTLSConfig) -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=config.certfile, keyfile=config.keyfile)
    context.load_verify_locations(cafile=config.ca_certfile)
    context.verify_mode = ssl.CERT_REQUIRED if config.require_client_cert else ssl.CERT_OPTIONAL
    return context


def create_client_ssl_context(
    *,
    ca_certfile: str,
    certfile: str | None = None,
    keyfile: str | None = None,
) -> ssl.SSLContext:
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=ca_certfile)
    if certfile is not None:
        context.load_cert_chain(certfile=certfile, keyfile=keyfile)
    return context


__all__ = ["MTLSConfig", "create_client_ssl_context", "create_server_ssl_context"]
