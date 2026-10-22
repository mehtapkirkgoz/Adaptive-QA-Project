"""Only repeated matching observations can produce an advisory signal."""

import unittest
from unittest.mock import patch
import test_dashboard_runs as fixtures
from adaptive_qa.flaky_signals import build_flaky_report
from adaptive_qa.execution_context import capture_execution_context
from adaptive_qa.models import TestResult, TestStatus
from adaptive_qa.project_store import ProjectNotFound


class FlakySignalsTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.DashboardRunsTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def observe(self, status, context='a' * 64):
        f = self.f
        run = f.submit()
        work = f.runs.claim_next()
        f.runs.record_result(work, TestResult('LOGIN-001', status, .1, 'private input'))
        if context is not None:
            f.runs.record_execution_context(work, context)
        f.runs.finish(work)
        return run

    def report(self):
        return build_flaky_report(self.f.runs, self.f.actor, self.f.pid)

    def test_four_alternations_are_insufficient_then_fifth_is_advisory(self):
        for status in (TestStatus.PASSED, TestStatus.FAILED) * 2:
            self.observe(status)
        self.assertFalse(self.report()['signals'][0]['potential_flakiness'])
        self.observe(TestStatus.PASSED)
        signal = self.report()['signals'][0]
        self.assertTrue(signal['potential_flakiness'])
        self.assertEqual(signal['transitions'], 4)
        self.assertEqual(signal['observations'], 5)
        self.assertNotIn('private input', str(self.report()))

    def test_different_contexts_are_not_pooled_and_legacy_is_excluded(self):
        for index, status in enumerate((TestStatus.PASSED, TestStatus.FAILED) * 3):
            self.observe(status, context=('a' if index % 2 else 'b') * 64)
        self.observe(TestStatus.PASSED, context=None)
        report = self.report()
        self.assertEqual(len(report['signals']), 2)
        self.assertEqual(report['excluded_runs'], 1)
        self.assertTrue(all(not row['potential_flakiness'] and row['observations'] == 3 for row in report['signals']))

    def test_single_transition_and_execution_errors_are_not_flaky(self):
        for status in (TestStatus.PASSED,) * 3 + (TestStatus.FAILED,) * 2:
            self.observe(status)
        self.observe(TestStatus.ERROR)
        signal = self.report()['signals'][0]
        self.assertEqual(signal['observations'], 5)
        self.assertEqual(signal['assessment'], 'mixed_outcomes')
        self.assertFalse(signal['potential_flakiness'])

    def test_other_owner_cannot_query_history(self):
        with self.assertRaises(ProjectNotFound):
            build_flaky_report(self.f.runs, self.f.other, self.f.pid)

    def test_context_capture_is_stable_bounded_and_missing_sources_are_unknown(self):
        value = capture_execution_context()
        self.assertRegex(value, '^[0-9a-f]{64}$')
        self.assertEqual(capture_execution_context(), value)
        with patch('adaptive_qa.execution_context.Path.open', side_effect=OSError):
            self.assertIsNone(capture_execution_context())
