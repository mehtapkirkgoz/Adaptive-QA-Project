"""Public profile validation never grants a private-address exception."""

import unittest
from unittest.mock import patch

from adaptive_qa.config import ProjectConfig
from adaptive_qa.crawler import CrawlBudget
from adaptive_qa.discovery_target import validate_discovery_project, validate_discovery_url
from adaptive_qa.local_discovery import discover_configured_target, _collect_project


class ConfiguredDiscoveryTests(unittest.TestCase):
    def project(self, url='https://qa.example.test/start', host='qa.example.test'):
        return ProjectConfig('configured', 'Configured discovery', url, (host,))

    def test_shape_validation_performs_no_dns_or_connection(self):
        with patch('socket.getaddrinfo', side_effect=AssertionError('No DNS')), \
                patch('socket.socket', side_effect=AssertionError('No connection')):
            validate_discovery_project(self.project(), 'public_https')
            with self.assertRaises(ValueError):
                validate_discovery_url('https://other.example.test/', self.project(), 'public_https')

    def test_private_non_https_ambiguous_and_secret_start_urls_fail_before_spawn(self):
        entries = [('http://qa.example.test/', 'qa.example.test'),
                   ('https://qa.example.test:444/', 'qa.example.test'),
                   ('https://127.0.0.1/', '127.0.0.1'), ('https://192.168.1.2/', '192.168.1.2'),
                   ('https://169.254.169.254/', '169.254.169.254'), ('https://localhost/', 'localhost'),
                   ('https://127.1/', '127.1'), ('https://qa.example.test/?token=private', 'qa.example.test'),
                   ('https://qa.example.test/#private', 'qa.example.test')]
        with patch('adaptive_qa.local_discovery.subprocess.Popen') as spawn:
            for url, host in entries:
                with self.subTest(url=url), self.assertRaises(ValueError):
                    discover_configured_target(self.project(url, host))
            spawn.assert_not_called()

    def test_controlled_profile_cannot_authorize_other_origins_or_profiles(self):
        for profile in ('controlled_local', 'unknown', True):
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                validate_discovery_project(self.project(), profile)

    def test_public_collector_uses_public_guard_before_browser_or_proxy_startup(self):
        class StopBeforeNetwork(Exception): pass
        with patch('adaptive_qa.local_discovery.EgressProxy', side_effect=StopBeforeNetwork) as proxy:
            with self.assertRaises(StopBeforeNetwork):
                _collect_project(self.project(), CrawlBudget(), 'public_https')
        guard = proxy.call_args.args[0]
        self.assertFalse(guard.local_sample)
        self.assertEqual(guard.policy.allowed_schemes, ('https',))
        self.assertEqual(guard.policy.allowed_ports, (443,))
        with patch('adaptive_qa.egress.resolve_with_deadline', return_value=('93.184.216.34', '127.0.0.1')), \
                patch('socket.socket', side_effect=AssertionError('Private IP must never connect')):
            with self.assertRaises(ValueError):
                guard.authorize('https://qa.example.test/start')

    def test_precancel_returns_non_executing_unknown_plan_without_spawning(self):
        with patch('adaptive_qa.local_discovery.subprocess.Popen') as spawn:
            result = discover_configured_target(self.project(), should_cancel=lambda: True)
        spawn.assert_not_called()
        self.assertEqual(result['pages'], [])
        self.assertIn('cancelled', result['limitations'])
        self.assertFalse(result['plan']['execution_authorized'])
