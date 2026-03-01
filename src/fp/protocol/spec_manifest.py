"""Auto-generated spec sync manifest. Do not edit manually."""

from __future__ import annotations

SCHEMA_SYNC_VERSION = 1
CORE_SCHEMA_PATH = '/Users/bangliu/Documents/ChatSCI/foundation-protocol/spec/fp-core.schema.json'
OPENRPC_SCHEMA_PATH = '/Users/bangliu/Documents/ChatSCI/foundation-protocol/spec/fp-openrpc.json'
CORE_SCHEMA_SHA256 = '71c29e8e355de445d10586ad08e8c7e55f1bc2843ad14c275e23dfc35687e745'
OPENRPC_SCHEMA_SHA256 = 'a108a95bbb81d0cacf626b808afa7c8c294f018df6d9373772408a141c917e9d'
CORE_DEFS = ('Activity', 'ActivityState', 'CapabilitySummary', 'Delegation', 'DelegationConstraints', 'DelegationSpendLimit', 'Dispute', 'Entity', 'EntityKind', 'Envelope', 'Error', 'Event', 'FpFamily', 'Identifier', 'Identity', 'Membership', 'MembershipStatus', 'MeterRecord', 'Organization', 'OrganizationGovernance', 'PrivacyControl', 'ProvenanceRecord', 'Receipt', 'RoleMap', 'Session', 'SessionBudget', 'SessionState', 'Settlement', 'SettlementStatus', 'Timestamp', 'Uri')
OPENRPC_METHODS = ('fp/activities.cancel', 'fp/activities.get', 'fp/activities.list', 'fp/activities.result', 'fp/activities.start', 'fp/activities.update', 'fp/entities.get', 'fp/entities.search', 'fp/events.ack', 'fp/events.pushConfig.delete', 'fp/events.pushConfig.get', 'fp/events.pushConfig.list', 'fp/events.pushConfig.set', 'fp/events.resubscribe', 'fp/events.stream', 'fp/initialize', 'fp/initialized', 'fp/orgs.create', 'fp/orgs.get', 'fp/orgs.members.add', 'fp/orgs.members.remove', 'fp/orgs.roles.grant', 'fp/orgs.roles.revoke', 'fp/ping', 'fp/sessions.close', 'fp/sessions.create', 'fp/sessions.get', 'fp/sessions.join', 'fp/sessions.leave', 'fp/sessions.update')

__all__ = [
    "SCHEMA_SYNC_VERSION",
    "CORE_SCHEMA_PATH",
    "OPENRPC_SCHEMA_PATH",
    "CORE_SCHEMA_SHA256",
    "OPENRPC_SCHEMA_SHA256",
    "CORE_DEFS",
    "OPENRPC_METHODS",
]
