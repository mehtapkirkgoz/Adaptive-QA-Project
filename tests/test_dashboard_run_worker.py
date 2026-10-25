"""Owned run execution boundaries with real storage and controlled adapter outcomes."""

from dataclasses import replace
import unittest
from unittest.mock import patch

import test_dashboard_runs as run_fixtures
from adaptive_qa.dashboard_run_worker import process_run_once
from adaptive_qa.models import TestResult, TestStatus


class DashboardRunWorkerTests(unittest.TestCase):
    def setUp(self):
        fixture = run_fixtures.DashboardRunsTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.queue = fixture.runs
        self.run = fixture.submit(('LOGIN-001', 'LOGIN-002'))

    def current(self):
        return self.queue.get(self.fixture.actor, self.fixture.pid, self.run['run_id'])

    def test_admitted_document_uses_independent_binding_without_guessing_comparison_context(self):
        self.queue.cancel(self.fixture.actor, self.fixture.pid, self.run['run_id'])
        document = self.fixture.submit(('DOC-001',))
        result = TestResult('DOC-001', TestStatus.PASSED, .1, 'Document passed.')
        with patch('adaptive_qa.dashboard_run_worker.run_isolated_document_test', return_value=result) as adapter, \
                patch.object(self.queue, 'record_execution_context') as record:
            self.assertEqual(process_run_once(self.queue)['status'], 'completed')
            self.assertEqual(adapter.call_args.kwargs['profile'], 'controlled_local')
            record.assert_not_called()
        self.assertIsNone(self.queue.comparison_context(self.fixture.actor, self.fixture.pid, document['run_id'])['execution_context'])

    def test_case_failure_preserves_actual_results_and_completed_lifecycle(self):
        results = [TestResult('LOGIN-001', TestStatus.PASSED, .1, 'PRIVATE /local/path'),
                   TestResult('LOGIN-002', TestStatus.FAILED, .2, 'PRIVATE second assertion')]
        with patch('adaptive_qa.dashboard_run_worker.run_isolated_sample_test', side_effect=results):
            self.assertEqual(process_run_once(self.queue)['status'], 'completed')
        current = self.current()
        self.assertEqual([r['status'] for r in current['results']], ['passed', 'failed'])
        self.assertNotIn('PRIVATE', str(current))
        self.assertNotIn('claim_token', current)

    def test_active_cancel_discards_late_result_and_leaves_unattempted_cases_unreported(self):
        def execute(case_id, **kwargs):
            self.queue.cancel(self.fixture.actor, self.fixture.pid, self.run['run_id'])
            self.assertTrue(kwargs['should_cancel']())
            return TestResult(case_id, TestStatus.PASSED, .1, 'Late result')
        with patch('adaptive_qa.dashboard_run_worker.run_isolated_sample_test', side_effect=execute) as adapter:
            self.assertEqual(process_run_once(self.queue)['status'], 'cancelled')
        self.assertEqual(adapter.call_count, 1)
        self.assertEqual(self.current()['results'], [])

    def test_configuration_change_before_execution_prevents_adapter_call(self):
        self.fixture.projects.save_configuration(self.fixture.actor, self.fixture.pid,
            dict(self.fixture.settings, allow_data_changes=True))
        with patch('adaptive_qa.dashboard_run_worker.run_isolated_sample_test') as adapter:
            self.assertEqual(process_run_once(self.queue)['status'], 'error')
        adapter.assert_not_called()

    def test_policy_change_during_execution_cannot_publish_a_result(self):
        def execute(case_id, **kwargs):
            self.fixture.projects.save_configuration(self.fixture.actor, self.fixture.pid,
                dict(self.fixture.settings, allow_data_changes=True))
            self.assertTrue(kwargs['should_cancel']())
            return TestResult(case_id, TestStatus.PASSED, .1, 'Obsolete policy')
        with patch('adaptive_qa.dashboard_run_worker.run_isolated_sample_test', side_effect=execute):
            self.assertEqual(process_run_once(self.queue)['status'], 'error')
        self.assertEqual(self.current()['results'], [])

    def test_invalid_adapter_result_and_exception_fail_without_fabricated_pass(self):
        with patch('adaptive_qa.dashboard_run_worker.run_isolated_sample_test', return_value='not a result'):
            self.assertEqual(process_run_once(self.queue)['status'], 'error')
        self.assertEqual(self.current()['results'], [])

    def test_claim_order_and_recovery_preserve_completed_progress(self):
        work = self.queue.claim_next()
        with self.assertRaises(ValueError):
            self.queue.record_result(replace(work, claim_token='wrong'), TestResult('LOGIN-001', TestStatus.PASSED, .1, 'x'))
        with self.assertRaises(ValueError):
            self.queue.record_result(work, TestResult('LOGIN-002', TestStatus.PASSED, .1, 'out of order'))
        self.queue.record_result(work, TestResult('LOGIN-001', TestStatus.PASSED, .1, 'valid'))
        self.assertEqual(self.queue.recover_interrupted(), {'cancelled': 0, 'error': 1})
        self.assertEqual(len(self.current()['results']), 1)
        with self.assertRaises(ValueError):
            self.queue.finish(work)

    def test_worker_lock_excludes_recovery_during_adapter_execution(self):
        def execute(case_id, **kwargs):
            with self.assertRaises(ValueError):
                self.queue.recover_interrupted()
            return TestResult(case_id, TestStatus.PASSED, .1, 'valid')
        with patch('adaptive_qa.dashboard_run_worker.run_isolated_sample_test', side_effect=execute):
            self.assertEqual(process_run_once(self.queue)['status'], 'completed')
