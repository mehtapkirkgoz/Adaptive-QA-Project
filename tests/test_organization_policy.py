"""Behavioral role isolation and admission boundaries for two organizations."""

import unittest
from dataclasses import FrozenInstanceError

from adaptive_qa.organization_policy import (
    OrganizationAction as Action, OrganizationRole as Role,
    OrganizationMembership, OrganizationQuota, permits,
)
from adaptive_qa.project_store import ProjectActor


class OrganizationPolicyTests(unittest.TestCase):
    def setUp(self):
        self.actor = ProjectActor('a' * 32)
        self.organization = 'b' * 32

    def membership(self, role):
        return OrganizationMembership(self.organization, self.actor.user_id, role)

    def test_role_matrix_denies_ungranted_actions(self):
        expected = {Role.OWNER: set(Action),
                    Role.ADMIN: {Action.READ, Action.CONFIGURE, Action.EXECUTE, Action.MANAGE_MEMBERS},
                    Role.MEMBER: {Action.READ, Action.EXECUTE}, Role.VIEWER: {Action.READ}}
        for role in Role:
            for action in Action:
                with self.subTest(role=role, action=action):
                    self.assertEqual(permits(self.actor, self.membership(role), self.organization, action),
                                     action in expected[role])

    def test_owner_of_one_organization_cannot_access_another(self):
        membership = self.membership(Role.OWNER)
        for action in Action:
            self.assertFalse(permits(self.actor, membership, 'c' * 32, action))
            self.assertFalse(permits(ProjectActor('d' * 32), membership, self.organization, action))

    def test_untrusted_claims_fail_closed(self):
        membership = self.membership(Role.OWNER)
        for actor, member, action in ((self.actor.user_id, membership, Action.READ),
                                      (self.actor, {'role': 'owner'}, Action.READ),
                                      (self.actor, membership, 'read')):
            self.assertFalse(permits(actor, member, self.organization, action))

    def test_membership_rejects_invalid_identities_and_string_role(self):
        for organization, user, role in (('', 'a' * 32, Role.OWNER),
                                         ('b' * 32, 'invalid', Role.OWNER),
                                         ('b' * 32, 'a' * 32, 'owner')):
            with self.assertRaises(ValueError):
                OrganizationMembership(organization, user, role)
        with self.assertRaises(FrozenInstanceError):
            self.membership(Role.VIEWER).role = Role.OWNER

    def test_capacity_boundary_and_invalid_counters(self):
        quota = OrganizationQuota(2, 3, 1, 4)
        for resource, limit in (('projects', 2), ('pending_runs', 3), ('active_runs', 1), ('daily_runs', 4)):
            self.assertTrue(quota.admits(resource, limit - 1))
            for count in (limit, limit + 1, -1, True, 0.5, '0', None):
                self.assertFalse(quota.admits(resource, count))
        for resource in ('unknown', None, []):
            self.assertFalse(quota.admits(resource, 0))

    def test_quotas_reject_boolean_zero_and_unbounded_limits(self):
        for name in ('max_projects', 'max_pending_runs', 'max_active_runs', 'max_daily_runs'):
            for value in (True, 0, -1, 10001, 1.5, '1'):
                with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                    OrganizationQuota(**{name: value})


if __name__ == '__main__':
    unittest.main()
