"""Plan review cannot invent coverage or authorize execution."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from adaptive_qa.dashboard_plan import review_project_plan, ConfigurationRequired
from adaptive_qa.project_store import ProjectStore, ProjectActor, ProjectNotFound


class DashboardPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = ProjectStore(Path(self.temp.name) / 'projects.sqlite')
        self.actor = ProjectActor('a' * 32)
        self.project = self.store.create(self.actor, 'Plan project')

    def save(self, changes=False):
        self.store.save_configuration(self.actor, self.project.project_id,
            {'base_url': 'https://example.test/', 'allowed_hosts': ['example.test'],
             'allow_data_changes': changes, 'secret_references': {}})

    def test_unconfigured_requires_settings_and_other_owner_is_not_found(self):
        with self.assertRaises(ConfigurationRequired):
            review_project_plan(self.store, self.actor, self.project.project_id)
        with self.assertRaises(ProjectNotFound):
            review_project_plan(self.store, ProjectActor('b' * 32), self.project.project_id)

    def test_review_never_visits_target_or_resolves_secrets_or_invents_findings(self):
        self.save()
        with patch('socket.create_connection', side_effect=AssertionError('No networking')), \
             patch('adaptive_qa.secrets.SecretReference.resolve', side_effect=AssertionError('No secret resolution')):
            result = review_project_plan(self.store, self.actor, self.project.project_id)
        self.assertFalse(result['execution_authorized'])
        self.assertEqual(result['inspected_pages'], 0)
        self.assertEqual(result['counts'], {'catalog': 86, 'selected': 0, 'skipped': 0, 'blocked': 86})
        self.assertTrue(all(f['status'] == 'unknown' for f in result['features']))
        self.assertEqual(len({c['case_id'] for c in result['cases']}), 86)

    def test_enabling_data_changes_does_not_authorize_or_select_cases(self):
        self.save(changes=True)
        result = review_project_plan(self.store, self.actor, self.project.project_id)
        self.assertFalse(result['execution_authorized'])
        self.assertEqual(result['counts']['selected'], 0)
        api_cases = [c for c in result['cases'] if c['test_type'] == 'api']
        self.assertEqual(len(api_cases), 20)
        self.assertTrue(all('adapter' in c['reason'] for c in api_cases))
