"""Minimal HS256 JWT authenticator."""

from __future__ import annotations

import base64
import hmac
import json
import time
from hashlib import sha256
from typing import Any

from .auth import Principal, extract_bearer_token


def encode_hs256_jwt(payload: dict[str, Any], secret: str, *, header: dict[str, Any] | None = None) -> str:
    head = dict(header or {"alg": "HS256", "typ": "JWT"})
    encoded_head = _b64url_encode(json.dumps(head, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    encoded_payload = _b64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signing_input = f"{encoded_head}.{encoded_payload}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, sha256).digest()
    return f"{encoded_head}.{encoded_payload}.{_b64url_encode(signature)}"


def decode_hs256_jwt(token: str, secret: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("jwt must have three segments")
    encoded_head, encoded_payload, encoded_signature = parts
    header = _json_loads(_b64url_decode(encoded_head))
    if header.get("alg") != "HS256":
        raise ValueError("unsupported jwt alg")

    signing_input = f"{encoded_head}.{encoded_payload}".encode("ascii")
    expected = hmac.new(secret.encode("utf-8"), signing_input, sha256).digest()
    provided = _b64url_decode(encoded_signature)
    if not hmac.compare_digest(expected, provided):
        raise ValueError("invalid jwt signature")

    payload = _json_loads(_b64url_decode(encoded_payload))
    if not isinstance(payload, dict):
        raise ValueError("jwt payload must be object")
    return payload


class JWTAuthenticator:
    """HS256 JWT authenticator suitable for service-to-service FP calls."""

    def __init__(
        self,
        *,
        secret: str,
        issuer: str | None = None,
        audience: str | None = None,
        leeway_seconds: int = 0,
    ) -> None:
        if not secret:
            raise ValueError("secret must be non-empty")
        self._secret = secret
        self._issuer = issuer
        self._audience = audience
        self._leeway = int(leeway_seconds)

    def authenticate(self, credentials: str | None) -> Principal | None:
        token = extract_bearer_token(credentials)
        if token is None:
            return None
        try:
            claims = decode_hs256_jwt(token, self._secret)
        except ValueError:
            return None

        if not self._validate_claims(claims):
            return None
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject:
            return None
        subject_type = claims.get("subject_type")
        if not isinstance(subject_type, str) or not subject_type:
            subject_type = "entity"
        return Principal(principal_id=subject, subject_type=subject_type)

    def _validate_claims(self, claims: dict[str, Any]) -> bool:
        now = int(time.time())
        exp = _as_int_or_none(claims.get("exp"))
        if exp is not None and now > exp + self._leeway:
            return False
        nbf = _as_int_or_none(claims.get("nbf"))
        if nbf is not None and now + self._leeway < nbf:
            return False
        iat = _as_int_or_none(claims.get("iat"))
        if iat is not None and now + self._leeway < iat:
            return False

        if self._issuer is not None and claims.get("iss") != self._issuer:
            return False
        if self._audience is not None:
            aud = claims.get("aud")
            if isinstance(aud, str):
                if aud != self._audience:
                    return False
            elif isinstance(aud, list):
                if self._audience not in aud:
                    return False
            else:
                return False
        return True


def _as_int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    return None


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * ((4 - len(raw) % 4) % 4)
    return base64.urlsafe_b64decode((raw + padding).encode("ascii"))


def _json_loads(raw: bytes) -> dict[str, Any]:
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("jwt segment must decode to object")
    return value


__all__ = ["JWTAuthenticator", "decode_hs256_jwt", "encode_hs256_jwt"]
