"""Environment separation and non-activation guarantees for deployment planning."""

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from adaptive_qa.deployment import DeploymentPlan, Environment
from adaptive_qa.__main__ import main


class DeploymentPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_environment_paths_are_separate_and_plan_does_not_create_them(self):
        staging = DeploymentPlan(Environment.STAGING, self.root, 'https://staging.example.test/')
        production = DeploymentPlan(Environment.PRODUCTION, self.root, 'https://qa.example.test:443')
        self.assertNotEqual(staging.directory, production.directory)
        self.assertEqual(staging.public_origin, 'https://staging.example.test')
        self.assertEqual(production.public_origin, 'https://qa.example.test')
        self.assertFalse(staging.directory.exists())
        self.assertFalse(production.directory.exists())
        self.assertTrue(staging.describe()['secure_cookies_required'])
        self.assertFalse(production.describe()['activation_enabled'])

    def test_local_plan_requires_explicit_numeric_loopback_and_port(self):
        plan = DeploymentPlan(Environment.LOCAL, self.root, 'http://127.0.0.1:8765')
        self.assertFalse(plan.describe()['secure_cookies_required'])
        for origin in ('http://localhost:8765', 'http://0.0.0.0:8765', 'http://127.0.0.1', 'http://127.0.0.1:80'):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                DeploymentPlan(Environment.LOCAL, self.root, origin)

    def test_public_profiles_reject_insecure_ambiguous_and_injected_origins(self):
        for origin in ('http://qa.example.test', 'https://127.0.0.1', 'https://localhost',
            'https://qa.example.test:8443', 'https://user:secret@qa.example.test',
            'https://qa.example.test/path', 'https://qa.example.test?x=1',
            'https://qa.example.test#', 'https://qa.example.test\n', 'https://*.example.test',
            'https://qa.example.local', 'https://qa.example.test./'):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                DeploymentPlan(Environment.STAGING, self.root, origin)

    def test_untyped_environment_and_unsafe_data_roots_are_rejected(self):
        with self.assertRaises(ValueError):
            DeploymentPlan('staging', self.root, 'https://qa.example.test')
        for root in (Path('relative'), Path(self.root.anchor), self.root / '..' / 'other'):
            with self.subTest(root=root), self.assertRaises(ValueError):
                DeploymentPlan(Environment.STAGING, root, 'https://qa.example.test')

    def test_existing_environment_symlink_cannot_redirect_to_production(self):
        (self.root / 'production').mkdir()
        try:
            (self.root / 'staging').symlink_to(self.root / 'production', target_is_directory=True)
        except OSError:
            self.skipTest('Symlink creation is unavailable for this Windows account.')
        with self.assertRaises(ValueError):
            DeploymentPlan(Environment.STAGING, self.root, 'https://qa.example.test')

    def test_cli_outputs_a_plan_without_files_network_or_service_activation(self):
        output = StringIO()
        with patch('sys.argv', ['adaptive-qa', 'deployment', 'plan', '--environment', 'staging',
                   '--data-root', str(self.root), '--origin', 'https://qa.example.test']), \
             patch('socket.socket', side_effect=AssertionError('No network')), \
             patch('subprocess.Popen', side_effect=AssertionError('No processes')), redirect_stdout(output):
            main()
        result = json.loads(output.getvalue())
        self.assertFalse(result['activation_enabled'])
        self.assertEqual(list(self.root.iterdir()), [])
