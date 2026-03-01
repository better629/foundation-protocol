"""Ed25519 signing helpers (backed by cryptography when available)."""

from __future__ import annotations

import base64

try:  # pragma: no cover - import guard
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

    _HAS_CRYPTO = True
except Exception:  # pragma: no cover - optional dependency
    InvalidSignature = Exception
    Ed25519PrivateKey = None
    Ed25519PublicKey = None
    serialization = None
    _HAS_CRYPTO = False


def ed25519_available() -> bool:
    return _HAS_CRYPTO


def generate_ed25519_keypair_pem() -> tuple[str, str]:
    _require_crypto()
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    private_pem = private.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = public.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return private_pem, public_pem


def sign_ed25519(payload: bytes, private_key_pem: str) -> str:
    _require_crypto()
    private = serialization.load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
    signature = private.sign(payload)
    return base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")


def verify_ed25519(payload: bytes, signature: str, public_key_pem: str) -> bool:
    _require_crypto()
    padded = signature + "=" * ((4 - len(signature) % 4) % 4)
    raw_signature = base64.urlsafe_b64decode(padded.encode("ascii"))
    public = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
    try:
        public.verify(raw_signature, payload)
    except InvalidSignature:
        return False
    return True


def _require_crypto() -> None:
    if not _HAS_CRYPTO:
        raise RuntimeError("cryptography package is required for Ed25519 operations")


__all__ = [
    "ed25519_available",
    "generate_ed25519_keypair_pem",
    "sign_ed25519",
    "verify_ed25519",
]
