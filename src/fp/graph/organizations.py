"""Organization creation and retrieval."""

from __future__ import annotations

from fp.protocol import Entity, EntityKind, FPError, FPErrorCode, Organization, OrganizationGovernance
from fp.stores.interfaces import EntityStore, OrganizationStore


class OrganizationRegistry:
    def __init__(self, entity_store: EntityStore, organization_store: OrganizationStore) -> None:
        self._entity_store = entity_store
        self._organization_store = organization_store

    def create(self, organization: Organization) -> Organization:
        if self._organization_store.get(organization.organization_id) is not None:
            raise FPError(
                FPErrorCode.ALREADY_EXISTS,
                message=f"organization already exists: {organization.organization_id}",
            )
        self._entity_store.put(organization.entity)
        self._organization_store.put(organization)
        return organization

    def create_from_entity(
        self,
        *,
        organization_id: str,
        entity: Entity,
        governance: OrganizationGovernance,
    ) -> Organization:
        if entity.kind is not EntityKind.ORGANIZATION:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "entity.kind must be organization")
        organization = Organization(
            organization_id=organization_id,
            entity=entity,
            governance=governance,
        )
        return self.create(organization)

    def get(self, organization_id: str) -> Organization:
        organization = self._organization_store.get(organization_id)
        if organization is None:
            raise FPError(FPErrorCode.NOT_FOUND, f"organization not found: {organization_id}")
        return organization

    def list(self) -> list[Organization]:
        return self._organization_store.list()
