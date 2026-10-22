"""Organization project quotas, role changes and personal-project isolation."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from adaptive_qa.organization_admission import OrganizationCapacityExceeded
from adaptive_qa.organization_policy import OrganizationQuota, OrganizationRole as Role
from adaptive_qa.organization_store import OrganizationStore, OrganizationNotFound
from adaptive_qa.organization_projects import OrganizationProjects
from adaptive_qa.project_store import ProjectStore, ProjectActor, ProjectNotFound
from adaptive_qa.project_settings import reference_name


class OrganizationProjectsTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.personal = ProjectStore(Path(self.temp.name) / 'projects.sqlite')
        self.organizations = OrganizationStore(self.personal)
        self.store = OrganizationProjects(self.organizations)
        self.owner, self.member, self.other = [ProjectActor(c * 32) for c in 'abc']
        self.org = self.organizations.create(self.owner, 'One', quota=OrganizationQuota(2, 2, 1, 5))
        self.second = self.organizations.create(self.other, 'Two')

    def test_parallel_creation_cannot_exceed_project_quota(self):
        def create(number):
            try:
                return self.store.create(self.owner, self.org, f'Project {number}')
            except OrganizationCapacityExceeded:
                return None
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = [value for value in pool.map(create, range(8)) if value]
        self.assertEqual(len(results), 2)
        self.assertEqual(len(self.store.list(self.owner, self.org)), 2)
        self.assertEqual(self.personal.list(self.owner), ())

    def test_viewer_reads_but_cannot_change_configuration_or_project(self):
        project = self.store.create(self.owner, self.org, 'Shared')
        self.organizations.set_member(self.owner, self.org, self.member.user_id, Role.VIEWER)
        self.assertEqual(self.store.get(self.member, self.org, project['project_id']), project)
        for action in (lambda: self.store.create(self.member, self.org, 'Forbidden'),
                       lambda: self.store.rename(self.member, self.org, project['project_id'], 'Forbidden'),
                       lambda: self.store.save_configuration(self.member, self.org, project['project_id'], {})):
            with self.assertRaises(OrganizationNotFound):
                action()
        self.organizations.remove_member(self.owner, self.org, self.member.user_id)
        with self.assertRaises(OrganizationNotFound):
            self.store.get(self.member, self.org, project['project_id'])

    def test_secret_references_use_organization_namespace_and_other_scope_is_denied(self):
        project = self.store.create(self.owner, self.org, 'Shared')
        project_id = project['project_id']
        settings = {'base_url': 'http://127.0.0.1:8000/', 'allowed_hosts': ['127.0.0.1'],
                    'allow_data_changes': False,
                    'secret_references': {'api_token': reference_name(self.org, project_id, 'api_token')}}
        result = self.store.save_configuration(self.owner, self.org, project_id, settings)
        self.assertEqual(result['secret_references']['api_token']['value'], '[REDACTED]')
        settings['secret_references']['api_token'] = reference_name(self.owner.user_id, project_id, 'api_token')
        with self.assertRaises(ValueError):
            self.store.save_configuration(self.owner, self.org, project_id, settings)
        with self.assertRaises(ProjectNotFound):
            self.store.get(self.other, self.second, project_id)
        with self.assertRaises(ProjectNotFound):
            self.personal.get(self.owner, project_id)

    def test_admin_can_configure_and_personal_projects_never_become_shared(self):
        private = self.personal.create(self.owner, 'Personal')
        self.organizations.set_member(self.owner, self.org, self.member.user_id, Role.ADMIN)
        shared = self.store.create(self.member, self.org, 'Shared')
        self.assertEqual(self.store.rename(self.member, self.org, shared['project_id'], 'Renamed')['name'], 'Renamed')
        with self.assertRaises(ProjectNotFound):
            self.store.get(self.member, self.org, private.project_id)
        with self.assertRaises(ProjectNotFound):
            self.personal.get(self.member, private.project_id)
