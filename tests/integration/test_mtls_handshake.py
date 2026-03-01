from __future__ import annotations

import ipaddress
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fp.app import FPClient, FPServer
from fp.protocol import FPError
from fp.security.mtls import MTLSConfig, create_client_ssl_context
from fp.transport import FPHTTPPublishedServer

try:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
except Exception:  # pragma: no cover - optional dependency
    x509 = None


def _generate_ca(cert_name: str) -> tuple[bytes, bytes]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cert_name)])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(minutes=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=2))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(private_key=key, algorithm=hashes.SHA256())
    )
    return (
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ),
        cert.public_bytes(serialization.Encoding.PEM),
    )


def _generate_signed_cert(
    *,
    common_name: str,
    issuer_key_pem: bytes,
    issuer_cert_pem: bytes,
    include_server_san: bool,
) -> tuple[bytes, bytes]:
    issuer_key = serialization.load_pem_private_key(issuer_key_pem, password=None)
    issuer_cert = x509.load_pem_x509_certificate(issuer_cert_pem)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])

    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(minutes=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=2))
    )
    if include_server_san:
        builder = builder.add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
            ),
            critical=False,
        )
    cert = builder.sign(private_key=issuer_key, algorithm=hashes.SHA256())
    return (
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ),
        cert.public_bytes(serialization.Encoding.PEM),
    )


@unittest.skipIf(x509 is None, "cryptography is required for mTLS handshake tests")
class MTLSHandshakeTests(unittest.TestCase):
    def test_mtls_rejects_client_without_cert_and_accepts_valid_client_cert(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ca_key, ca_cert = _generate_ca("FP Test CA")
            server_key, server_cert = _generate_signed_cert(
                common_name="localhost",
                issuer_key_pem=ca_key,
                issuer_cert_pem=ca_cert,
                include_server_san=True,
            )
            client_key, client_cert = _generate_signed_cert(
                common_name="fp-client",
                issuer_key_pem=ca_key,
                issuer_cert_pem=ca_cert,
                include_server_san=False,
            )

            ca_path = root / "ca.pem"
            server_cert_path = root / "server-cert.pem"
            server_key_path = root / "server-key.pem"
            client_cert_path = root / "client-cert.pem"
            client_key_path = root / "client-key.pem"
            ca_path.write_bytes(ca_cert)
            server_cert_path.write_bytes(server_cert)
            server_key_path.write_bytes(server_key)
            client_cert_path.write_bytes(client_cert)
            client_key_path.write_bytes(client_key)

            server = FPServer()
            with FPHTTPPublishedServer(
                server,
                publish_entity_id="fp:system:runtime",
                host="127.0.0.1",
                port=0,
                mtls=MTLSConfig(
                    certfile=str(server_cert_path),
                    keyfile=str(server_key_path),
                    ca_certfile=str(ca_path),
                    require_client_cert=True,
                ),
            ) as published:
                no_cert_context = create_client_ssl_context(ca_certfile=str(ca_path))
                no_cert_client = FPClient.from_http_jsonrpc(published.rpc_url, ssl_context=no_cert_context)
                with self.assertRaises(FPError):
                    no_cert_client.ping()

                cert_context = create_client_ssl_context(
                    ca_certfile=str(ca_path),
                    certfile=str(client_cert_path),
                    keyfile=str(client_key_path),
                )
                cert_client = FPClient.from_http_jsonrpc(published.rpc_url, ssl_context=cert_context)
                ping = cert_client.ping()
                self.assertEqual(ping["ok"], True)


if __name__ == "__main__":
    unittest.main()
