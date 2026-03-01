"""Card signing and verification helpers for FP directory records."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from fp.protocol import FPError, FPErrorCode
from fp.security.ed25519 import sign_ed25519, verify_ed25519

from .network import FPServerCard


def canonical_card_payload(card: FPServerCard) -> bytes:
    payload = card.to_dict()
    payload.pop("signature", None)
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_server_card(
    card: FPServerCard,
    *,
    private_key_pem: str,
    key_ref: str,
    ttl_seconds: int | None = None,
    now: datetime | None = None,
) -> FPServerCard:
    now_ts = (now or datetime.now(tz=timezone.utc)).astimezone(timezone.utc)
    issued_at = card.issued_at or _iso(now_ts)
    ttl = ttl_seconds if ttl_seconds is not None else card.ttl_seconds
    if ttl is None:
        ttl = 600
    expires_at = card.expires_at or _iso(now_ts + timedelta(seconds=ttl))

    unsigned = FPServerCard.from_dict(
        {
            **card.to_dict(),
            "sign_alg": "ed25519",
            "key_ref": key_ref,
            "issued_at": issued_at,
            "expires_at": expires_at,
            "ttl_seconds": ttl,
            "signature": "pending",
        }
    )
    signature = sign_ed25519(canonical_card_payload(unsigned), private_key_pem)
    signed_payload = unsigned.to_dict()
    signed_payload["signature"] = signature
    return FPServerCard.from_dict(signed_payload)


def verify_server_card(card: FPServerCard, *, public_keys: dict[str, str]) -> bool:
    if card.sign_alg in {None, "none"}:
        return card.signature in {None, "unsigned"}
    if card.sign_alg != "ed25519":
        raise FPError(FPErrorCode.INVALID_ARGUMENT, f"unsupported card signature algorithm: {card.sign_alg}")
    if not card.key_ref or not card.signature:
        return False
    public_key = public_keys.get(card.key_ref)
    if public_key is None:
        return False
    return verify_ed25519(canonical_card_payload(card), card.signature, public_key)


def ensure_not_expired(card: FPServerCard, *, now: datetime | None = None) -> None:
    if card.expires_at is None:
        return
    now_ts = (now or datetime.now(tz=timezone.utc)).astimezone(timezone.utc)
    expires = datetime.fromisoformat(card.expires_at.replace("Z", "+00:00")).astimezone(timezone.utc)
    if expires <= now_ts:
        raise FPError(
            FPErrorCode.NOT_FOUND,
            message="server card is expired",
            details={"entity_id": card.entity_id, "expires_at": card.expires_at},
        )


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = ["canonical_card_payload", "ensure_not_expired", "sign_server_card", "verify_server_card"]
