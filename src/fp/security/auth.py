"""Authentication primitives for FP runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class Principal:
    principal_id: str
    subject_type: str = "entity"


class Authenticator(Protocol):
    def authenticate(self, credentials: str | None) -> Principal | None: ...


class StaticTokenAuthenticator:
    """Minimal authenticator for local and integration environments."""

    def __init__(self, token_to_principal: dict[str, str]) -> None:
        self._token_to_principal = dict(token_to_principal)

    def authenticate(self, credentials: str | None) -> Principal | None:
        if credentials is None:
            return None
        principal_id = self._token_to_principal.get(credentials)
        if principal_id is None:
            return None
        return Principal(principal_id=principal_id)


def extract_bearer_token(authorization_header: str | None) -> str | None:
    if authorization_header is None:
        return None
    value = authorization_header.strip()
    if not value:
        return None
    parts = value.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        token = parts[1].strip()
        return token or None
    return value
