"""Integrity helper utilities for FP evidence objects."""

from __future__ import annotations

import hashlib
import hmac


def sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sign_hmac_sha256(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def verify_hmac_sha256(payload: bytes, secret: str, signature: str) -> bool:
    expected = sign_hmac_sha256(payload, secret)
    return hmac.compare_digest(expected, signature)
