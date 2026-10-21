"""Real persistence, ownership and non-resolving secret-reference boundaries."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from adaptive_qa.project_store import ProjectActor, ProjectStore, ProjectNotFound
from adaptive_qa.project_settings import reference_name


class ProjectSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'projects.sqlite'
        self.store = ProjectStore(self.path)
        self.owner, self.other = ProjectActor('a' * 32), ProjectActor('b' * 32)
        self.project = self.store.create(self.owner, 'Settings project')
        self.pid = self.project.project_id
        self.data = {'base_url': 'http://127.0.0.1:8000/', 'allowed_hosts': ['127.0.0.1'],
                     'allow_data_changes': False, 'secret_references': {}}

    def test_configuration_persists_and_rename_preserves_it(self):
        self.assertFalse(self.store.configuration(self.owner, self.pid)['configured'])
        result = self.store.save_configuration(self.owner, self.pid, self.data)
        self.store.rename(self.owner, self.pid, 'Renamed')
        reopened = ProjectStore(self.path).configuration(self.owner, self.pid)
        self.assertEqual(reopened, result)
        self.assertFalse(reopened['allow_data_changes'])

    def test_other_owner_and_missing_settings_have_identical_errors(self):
        self.store.save_configuration(self.owner, self.pid, self.data)
        for operation in ('configuration', 'save_configuration'):
            errors = []
            for actor, pid in ((self.other, self.pid), (self.owner, '0' * 32)):
                with self.assertRaises(ProjectNotFound) as error:
                    getattr(self.store, operation)(actor, pid, *([self.data] if operation == 'save_configuration' else []))
                errors.append(str(error.exception))
            self.assertEqual(errors[0], errors[1])

    def test_scoped_references_never_resolve_or_store_environment_values(self):
        name = reference_name(self.owner.user_id, self.pid, 'api_token')
        self.data['secret_references'] = {'api_token': name}
        with patch.dict('os.environ', {name: 'PRIVATE_ENV_SENTINEL'}), \
             patch('adaptive_qa.secrets.SecretReference.resolve', side_effect=AssertionError('Resolution is forbidden')), \
             patch('socket.create_connection', side_effect=AssertionError('Network is forbidden')):
            result = self.store.save_configuration(self.owner, self.pid, self.data)
            self.assertEqual(self.store.configuration(self.owner, self.pid), result)
        self.assertEqual(result['secret_references']['api_token']['value'], '[REDACTED]')
        self.assertNotIn('PRIVATE_ENV_SENTINEL', json.dumps(result))
        self.assertNotIn(b'PRIVATE_ENV_SENTINEL', self.path.read_bytes())

    def test_cross_project_cross_owner_and_arbitrary_references_are_denied(self):
        another = self.store.create(self.owner, 'Other project')
        for name in ('PATH', 'OPENAI_API_KEY', 'raw-secret-value',
                     reference_name(self.other.user_id, self.pid, 'api_token'),
                     reference_name(self.owner.user_id, another.project_id, 'api_token'),
                     reference_name(self.owner.user_id, self.pid, 'login_password')):
            with self.assertRaises(ValueError):
                self.store.save_configuration(self.owner, self.pid,
                    dict(self.data, secret_references={'api_token': name}))
        self.assertFalse(self.store.configuration(self.owner, self.pid)['configured'])

    def test_invalid_targets_hosts_policy_and_raw_secrets_are_rejected_atomically(self):
        original = self.store.save_configuration(self.owner, self.pid, self.data)
        for change in ({'base_url': 'https://user:password@example.test/'},
                       {'base_url': 'http://127.0.0.1:8000/?token=private'},
                       {'base_url': 'http://127.0.0.1:8000/#private'},
                       {'base_url': 'https://other.test/'},
                       {'allowed_hosts': ['127.0.0.1', '*.example.test']},
                       {'allowed_hosts': ['127.0.0.1', 'bad_host']},
                       {'allowed_hosts': ['127.0.0.1'] * 2},
                       {'allow_data_changes': 'true'}, {'api_token': 'PRIVATE'},
                       {'secret_references': {'unknown': 'PRIVATE'}}):
            with self.assertRaises(ValueError):
                self.store.save_configuration(self.owner, self.pid, dict(self.data, **change))
            self.assertEqual(self.store.configuration(self.owner, self.pid), original)

    def test_replacing_settings_removes_prior_references_and_resets_policy(self):
        name = reference_name(self.owner.user_id, self.pid, 'login_password')
        self.store.save_configuration(self.owner, self.pid,
            dict(self.data, allow_data_changes=True, secret_references={'login_password': name}))
        result = self.store.save_configuration(self.owner, self.pid, self.data)
        self.assertEqual(result['secret_references'], {})
        self.assertFalse(result['allow_data_changes'])
