"""Real process termination under controlled replacement children; no target traffic."""

import subprocess
import sys
from time import monotonic
import unittest
from unittest.mock import patch

from adaptive_qa.crawler import CrawlBudget
from adaptive_qa.local_discovery import discover_local_sample


class DiscoveryProcessTests(unittest.TestCase):
    def test_precancel_does_not_spawn(self):
        with patch('adaptive_qa.local_discovery.subprocess.Popen') as spawn:
            result = discover_local_sample(should_cancel=lambda: True)
        spawn.assert_not_called()
        self.assertIn('cancelled', result['limitations'])
        self.assertFalse(result['plan']['execution_authorized'])

    def run_owned_child(self, *, cancel=False, broken=False):
        original = subprocess.Popen
        children = []
        start = monotonic()
        def spawn(args, **kwargs):
            if 'adaptive_qa.local_discovery' not in args:
                return original(args, **kwargs)
            child = original([sys.executable, '-c', 'import time; time.sleep(60)'], **kwargs)
            children.append(child)
            return child
        def callback():
            if children and broken:
                raise RuntimeError('Trusted cancellation source failed.')
            return cancel and monotonic() - start > 0.2
        try:
            with patch('adaptive_qa.local_discovery.subprocess.Popen', side_effect=spawn):
                result = discover_local_sample(CrawlBudget(timeout_seconds=0.4), should_cancel=callback)
            self.assertEqual(result['pages'], [])
            self.assertIn('cancelled' if cancel else 'time_limit', result['limitations'])
            self.assertTrue(result['partial_results_discarded'])
            self.assertFalse(result['plan']['execution_authorized'])
        finally:
            for child in children:
                survived = child.poll() is None
                if survived:
                    child.kill()
                    child.wait(timeout=5)
                self.assertFalse(survived, 'Owned child survived supervisor exit.')

    def test_active_cancel_terminates_real_child(self):
        self.run_owned_child(cancel=True)

    def test_deadline_terminates_real_child(self):
        self.run_owned_child()

    def test_callback_failure_still_cleans_up_real_child(self):
        with self.assertRaisesRegex(RuntimeError, 'cancellation source'):
            self.run_owned_child(broken=True)
