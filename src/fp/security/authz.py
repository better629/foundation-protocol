"""Authorization primitives for FP runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .auth import Principal


class Authorizer(Protocol):
    def authorize(self, principal: Principal, action: str, resource: str) -> bool: ...


@dataclass(slots=True)
class ACLAuthorizer:
    """Simple ACL map with action/resource tuple keys."""

    acl: dict[tuple[str, str], set[str]] = field(default_factory=dict)

    def authorize(self, principal: Principal, action: str, resource: str) -> bool:
        allowlist = self.acl.get((action, resource), set())
        return principal.principal_id in allowlist
