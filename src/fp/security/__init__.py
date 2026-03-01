"""Security exports."""

from .auth import Principal, StaticTokenAuthenticator, extract_bearer_token
from .authz import ACLAuthorizer
from .ed25519 import ed25519_available, generate_ed25519_keypair_pem, sign_ed25519, verify_ed25519
from .jwt_auth import JWTAuthenticator, decode_hs256_jwt, encode_hs256_jwt
from .mtls import MTLSConfig, create_client_ssl_context, create_server_ssl_context
from .signatures import sha256_hex, sign_hmac_sha256, verify_hmac_sha256

__all__ = [
    "ACLAuthorizer",
    "JWTAuthenticator",
    "MTLSConfig",
    "Principal",
    "StaticTokenAuthenticator",
    "create_client_ssl_context",
    "create_server_ssl_context",
    "decode_hs256_jwt",
    "ed25519_available",
    "encode_hs256_jwt",
    "extract_bearer_token",
    "generate_ed25519_keypair_pem",
    "sign_ed25519",
    "sha256_hex",
    "verify_ed25519",
    "sign_hmac_sha256",
    "verify_hmac_sha256",
]
