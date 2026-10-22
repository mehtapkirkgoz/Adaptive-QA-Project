"""Real SQLite membership persistence, revocation and privilege boundaries."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from adaptive_qa.organization_policy import OrganizationRole as Role, OrganizationQuota
from adaptive_qa.organization_store import OrganizationStore, OrganizationNotFound
from adaptive_qa.project_store import ProjectStore, ProjectActor, ProjectNotFound


class OrganizationStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.projects = ProjectStore(Path(self.temp.name) / 'projects.sqlite')
        self.store = OrganizationStore(self.projects)
        self.owner = ProjectActor('a' * 32)
        self.other = ProjectActor('b' * 32)
        self.admin = ProjectActor('c' * 32)
        self.member = ProjectActor('d' * 32)
        self.one = self.store.create(self.owner, 'Organization one', quota=OrganizationQuota(3, 2, 1, 8))
        self.two = self.store.create(self.other, 'Organization two')

    def test_owner_membership_and_quotas_survive_reopening(self):
        reopened = OrganizationStore(ProjectStore(self.projects.database))
        self.assertEqual(reopened.membership(self.owner, self.one).role, Role.OWNER)
        self.assertEqual(reopened.quota(self.owner, self.one), OrganizationQuota(3, 2, 1, 8))

    def test_two_organizations_deny_cross_membership_reads_and_writes(self):
        for operation in (lambda: self.store.membership(self.owner, self.two),
                          lambda: self.store.quota(self.owner, self.two),
                          lambda: self.store.set_member(self.owner, self.two, self.member.user_id, Role.ADMIN),
                          lambda: self.store.membership(self.owner, 'f' * 32)):
            with self.assertRaisesRegex(OrganizationNotFound, '^Organization not found\\.$'):
                operation()
        self.assertEqual(self.store.membership(self.other, self.two).role, Role.OWNER)

    def test_admin_can_manage_members_but_not_owners_or_admin_peers(self):
        self.store.set_member(self.owner, self.one, self.admin.user_id, Role.ADMIN)
        self.store.set_member(self.admin, self.one, self.member.user_id, Role.MEMBER)
        self.assertEqual(self.store.membership(self.member, self.one).role, Role.MEMBER)
        for user, role in ((self.owner.user_id, Role.VIEWER), (self.admin.user_id, Role.VIEWER),
                           (self.member.user_id, Role.ADMIN)):
            with self.assertRaises(OrganizationNotFound):
                self.store.set_member(self.admin, self.one, user, role)
        self.store.remove_member(self.admin, self.one, self.member.user_id)
        with self.assertRaises(OrganizationNotFound):
            self.store.membership(self.member, self.one)

    def test_owner_cannot_be_removed_or_demoted_and_no_owner_promotion(self):
        with self.assertRaises(OrganizationNotFound):
            self.store.remove_member(self.owner, self.one, self.owner.user_id)
        with self.assertRaises(OrganizationNotFound):
            self.store.set_member(self.owner, self.one, self.owner.user_id, Role.MEMBER)
        with self.assertRaises(ValueError):
            self.store.set_member(self.owner, self.one, self.member.user_id, Role.OWNER)
        self.assertEqual(self.store.membership(self.owner, self.one).role, Role.OWNER)

    def test_revocation_and_demotion_take_effect_on_next_operation(self):
        self.store.set_member(self.owner, self.one, self.admin.user_id, Role.ADMIN)
        self.store.set_member(self.owner, self.one, self.admin.user_id, Role.VIEWER)
        with self.assertRaises(OrganizationNotFound):
            self.store.set_member(self.admin, self.one, self.member.user_id, Role.MEMBER)
        self.store.remove_member(self.owner, self.one, self.admin.user_id)
        with self.assertRaises(OrganizationNotFound):
            self.store.quota(self.admin, self.one)

    def test_membership_does_not_grant_access_to_historical_owner_projects(self):
        project = self.projects.create(self.owner, 'Private existing project')
        self.store.set_member(self.owner, self.one, self.member.user_id, Role.MEMBER)
        with self.assertRaises(ProjectNotFound):
            self.projects.get(self.member, project.project_id)
        self.assertEqual(self.projects.get(self.owner, project.project_id), project)


if __name__ == '__main__':
    unittest.main()
