"""Graph-domain runtime module."""

from __future__ import annotations

from fp.graph import EntityRegistry, MembershipRegistry, OrganizationRegistry
from fp.protocol import Entity, EntityKind, Membership, Organization


class GraphModule:
    def __init__(
        self,
        *,
        entities: EntityRegistry,
        organizations: OrganizationRegistry,
        memberships: MembershipRegistry,
    ) -> None:
        self.entities = entities
        self.organizations = organizations
        self.memberships = memberships

    def register_entity(self, entity: Entity) -> Entity:
        return self.entities.upsert(entity)

    def get_entity(self, entity_id: str) -> Entity:
        return self.entities.get(entity_id)

    def search_entities(self, *, query: str, kind: EntityKind | None = None, limit: int = 50) -> list[Entity]:
        return self.entities.search(query=query, kind=kind.value if kind else None, limit=limit)

    def create_organization(self, organization: Organization) -> Organization:
        return self.organizations.create(organization)

    def get_organization(self, organization_id: str) -> Organization:
        return self.organizations.get(organization_id)

    def add_membership(self, membership: Membership) -> Membership:
        return self.memberships.add(membership)

    def remove_membership(self, organization_id: str, membership_id: str) -> Membership:
        return self.memberships.remove(organization_id, membership_id)

    def grant_roles(self, organization_id: str, member_entity_id: str, roles: set[str]) -> Membership:
        return self.memberships.grant_roles(organization_id, member_entity_id, roles)

    def revoke_roles(self, organization_id: str, member_entity_id: str, roles: set[str]) -> Membership:
        return self.memberships.revoke_roles(organization_id, member_entity_id, roles)
