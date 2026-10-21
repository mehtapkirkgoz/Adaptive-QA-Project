"""Trusted local CLI boundaries without starting a persistent server."""

from argparse import Namespace
import getpass
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from adaptive_qa.auth_store import AuthStore
from adaptive_qa.dashboard_cli import run


class DashboardCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'auth.sqlite'

    def test_noninteractive_input_cannot_provision(self):
        with patch('adaptive_qa.dashboard_cli.sys.stdin.isatty', return_value=False):
            with self.assertRaisesRegex(ValueError, 'interactive terminal'):
                run(Namespace(dashboard_command='create-user', database=self.path))
        self.assertFalse(self.path.exists())

    def provision(self, confirmations):
        with patch('adaptive_qa.dashboard_cli.sys.stdin.isatty', return_value=True), \
             patch('adaptive_qa.dashboard_cli.sys.stdout.isatty', return_value=True), \
             patch('builtins.input', return_value='cli@example.test'), \
             patch('adaptive_qa.dashboard_cli.getpass.getpass', side_effect=confirmations), \
             patch('builtins.print') as output:
            run(Namespace(dashboard_command='create-user', database=self.path))
            return output

    def test_provisioned_account_can_authenticate_without_password_output(self):
        password = 'Local CLI password 123!'
        output = self.provision([password, password])
        self.assertNotIn(password, str(output.call_args_list))
        self.assertIsNotNone(AuthStore(self.path).login('cli@example.test', password))

    def test_confirmation_mismatch_does_not_create_database(self):
        with self.assertRaisesRegex(ValueError, 'do not match'):
            self.provision(['Local CLI password 123!', 'different'])
        self.assertFalse(self.path.exists())

    def test_unavailable_hidden_input_fails_before_account_creation(self):
        with self.assertRaisesRegex(ValueError, 'Hidden password input'):
            self.provision([getpass.GetPassWarning('Cannot hide password input.')])
        self.assertFalse(self.path.exists())

    def test_server_binds_loopback_without_proxy_trust_or_access_logs(self):
        with patch('uvicorn.run') as server, patch('builtins.print'):
            run(Namespace(dashboard_command='serve', database=self.path, port=8766))
        options = server.call_args.kwargs
        self.assertEqual(options['host'], '127.0.0.1')
        self.assertEqual(options['workers'], 1)
        self.assertFalse(options['proxy_headers'])
        self.assertFalse(options['access_log'])
        self.assertEqual(options['limit_concurrency'], 32)

    def test_invalid_port_does_not_create_database(self):
        with self.assertRaises(ValueError):
            run(Namespace(dashboard_command='serve', database=self.path, port=80))
        self.assertFalse(self.path.exists())
