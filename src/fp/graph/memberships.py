"""Membership and role mutation helpers."""

from __future__ import annotations

from dataclasses import replace

from fp.protocol import FPError, FPErrorCode, Membership, MembershipStatus, utc_now
from fp.stores.interfaces import MembershipStore, OrganizationStore


class MembershipRegistry:
    def __init__(self, organization_store: OrganizationStore, membership_store: MembershipStore) -> None:
        self._organization_store = organization_store
        self._membership_store = membership_store

    def add(self, membership: Membership) -> Membership:
        if self._organization_store.get(membership.organization_id) is None:
            raise FPError(
                FPErrorCode.NOT_FOUND,
                message=f"organization not found: {membership.organization_id}",
            )
        if self._membership_store.get(membership.membership_id) is not None:
            raise FPError(
                FPErrorCode.ALREADY_EXISTS,
                message=f"membership already exists: {membership.membership_id}",
            )
        self._membership_store.put(membership)
        return membership

    def remove(self, organization_id: str, membership_id: str) -> Membership:
        membership = self._membership_store.get(membership_id)
        if membership is None or membership.organization_id != organization_id:
            raise FPError(
                FPErrorCode.NOT_FOUND,
                message=f"membership not found: {membership_id}",
            )
        updated = replace(membership, status=MembershipStatus.REVOKED, updated_at=utc_now())
        self._membership_store.put(updated)
        return updated

    def grant_roles(self, organization_id: str, member_entity_id: str, roles: set[str]) -> Membership:
        membership = self._find_by_member(organization_id, member_entity_id)
        updated = replace(membership, roles=set(membership.roles) | set(roles), updated_at=utc_now())
        self._membership_store.put(updated)
        return updated

    def revoke_roles(self, organization_id: str, member_entity_id: str, roles: set[str]) -> Membership:
        membership = self._find_by_member(organization_id, member_entity_id)
        next_roles = set(membership.roles) - set(roles)
        if not next_roles:
            raise FPError(
                FPErrorCode.INVALID_ARGUMENT,
                "membership must keep at least one role",
            )
        updated = replace(membership, roles=next_roles, updated_at=utc_now())
        self._membership_store.put(updated)
        return updated

    def list_for_organization(self, organization_id: str) -> list[Membership]:
        return self._membership_store.by_organization(organization_id)

    def _find_by_member(self, organization_id: str, member_entity_id: str) -> Membership:
        for membership in self._membership_store.by_organization(organization_id):
            if membership.member_entity_id == member_entity_id and membership.status is MembershipStatus.ACTIVE:
                return membership
        raise FPError(
            FPErrorCode.NOT_FOUND,
            message=f"active membership not found for entity: {member_entity_id}",
        )
