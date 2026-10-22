"""Fail-closed organization permissions and bounded admission policy.

Memberships must come from trusted persistence, never HTTP request claims.
This module does not grant access to existing owner-scoped projects.
"""

from dataclasses import dataclass
from enum import Enum

from adaptive_qa.project_store import ProjectActor, _id


class OrganizationRole(Enum):
    OWNER = 'owner'
    ADMIN = 'admin'
    MEMBER = 'member'
    VIEWER = 'viewer'


class OrganizationAction(Enum):
    READ = 'read'
    CONFIGURE = 'configure'
    EXECUTE = 'execute'
    MANAGE_MEMBERS = 'manage_members'
    MANAGE_ORGANIZATION = 'manage_organization'


_PERMISSIONS = {
    OrganizationRole.OWNER: frozenset(OrganizationAction),
    OrganizationRole.ADMIN: frozenset({OrganizationAction.READ, OrganizationAction.CONFIGURE,
                                     OrganizationAction.EXECUTE, OrganizationAction.MANAGE_MEMBERS}),
    OrganizationRole.MEMBER: frozenset({OrganizationAction.READ, OrganizationAction.EXECUTE}),
    OrganizationRole.VIEWER: frozenset({OrganizationAction.READ}),
}


@dataclass(frozen=True)
class OrganizationMembership:
    organization_id: str
    user_id: str
    role: OrganizationRole

    def __post_init__(self):
        _id(self.organization_id)
        _id(self.user_id)
        if not isinstance(self.role, OrganizationRole):
            raise ValueError('A typed organization role is required.')


def permits(actor, membership, organization_id, action):
    """Unknown identities, roles, organizations and actions never authorize."""
    return (isinstance(actor, ProjectActor)
            and isinstance(membership, OrganizationMembership)
            and isinstance(action, OrganizationAction)
            and actor.user_id == membership.user_id
            and organization_id == membership.organization_id
            and action in _PERMISSIONS[membership.role])


@dataclass(frozen=True)
class OrganizationQuota:
    max_projects: int = 20
    max_pending_runs: int = 5
    max_active_runs: int = 1
    max_daily_runs: int = 100

    def __post_init__(self):
        for name, ceiling in (('max_projects', 1000), ('max_pending_runs', 100),
                              ('max_active_runs', 16), ('max_daily_runs', 10000)):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= ceiling:
                raise ValueError('Organization quota must use bounded positive integers.')

    def admits(self, resource, current):
        """Decision only; caller must read/check/reserve in one transaction."""
        limits = {'projects': self.max_projects, 'pending_runs': self.max_pending_runs,
                  'active_runs': self.max_active_runs, 'daily_runs': self.max_daily_runs}
        if not isinstance(resource, str) or resource not in limits:
            return False
        return type(current) is int and 0 <= current < limits[resource]
