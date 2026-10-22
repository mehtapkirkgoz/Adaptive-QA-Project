"""Explicit rerun admission and qualified historical outcome comparisons."""

import unittest
from unittest.mock import patch
import test_dashboard_runs as fixtures
from adaptive_qa.dashboard_reports import compare_runs
from adaptive_qa.dashboard_runs import TestRunNotFound
from adaptive_qa.models import TestResult, TestStatus


class DashboardHistoryTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.DashboardRunsTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def complete(self, status):
        run = self.f.submit()
        work = self.f.runs.claim_next()
        self.f.runs.record_result(work, TestResult('LOGIN-001', status, .1, 'private'))
        self.f.runs.finish(work)
        return run

    def compare(self, before, after):
        f = self.f
        return compare_runs(f.runs, f.actor, f.pid, before['run_id'], after['run_id'])

    def test_rerun_is_new_explicit_queued_work_with_owned_parent(self):
        f = self.f
        parent = self.complete(TestStatus.FAILED)
        before = f.runs.get(f.actor, f.pid, parent['run_id'])
        with patch('adaptive_qa.browser_process.run_isolated_sample_test', side_effect=AssertionError('No HTTP execution')):
            child = f.runs.submit(f.actor, f.pid, f.report_job, ('LOGIN-001',), rerun_of=parent['run_id'])
        self.assertNotEqual(child['run_id'], parent['run_id'])
        self.assertEqual(child['rerun_of'], parent['run_id'])
        self.assertEqual(child['results'], [])
        self.assertEqual(child['status'], 'queued')
        self.assertEqual(f.runs.get(f.actor, f.pid, parent['run_id']), before)

    def test_rerun_rechecks_parent_selection_current_policy_and_ownership(self):
        f = self.f
        parent = f.submit()
        with self.assertRaises(ValueError):
            f.runs.submit(f.actor, f.pid, f.report_job, ('LOGIN-001',), rerun_of=parent['run_id'])
        f.runs.cancel(f.actor, f.pid, parent['run_id'])
        with self.assertRaises(ValueError):
            f.runs.submit(f.actor, f.pid, f.report_job, ('SEARCH-001',), rerun_of=parent['run_id'])
        with self.assertRaises(TestRunNotFound):
            f.runs.submit(f.other, f.pid, f.report_job, ('LOGIN-001',), rerun_of=parent['run_id'])
        f.projects.save_configuration(f.actor, f.pid, dict(f.settings, allow_data_changes=True))
        with self.assertRaises(ValueError):
            f.runs.submit(f.actor, f.pid, f.report_job, ('LOGIN-001',), rerun_of=parent['run_id'])

    def test_status_changes_are_qualified_without_flaky_inference(self):
        first = self.complete(TestStatus.FAILED)
        second = self.complete(TestStatus.PASSED)
        report = self.compare(first, second)
        self.assertTrue(report['comparable'])
        self.assertEqual(report['results'], [{'case_id': 'LOGIN-001', 'baseline_status': 'failed',
            'current_status': 'passed', 'change': 'changed'}])
        self.assertIn('do not establish flakiness', report['reason'])

    def test_cancelled_unattempted_results_are_explicit_not_passed(self):
        f = self.f
        first = self.complete(TestStatus.PASSED)
        second = f.submit()
        f.runs.cancel(f.actor, f.pid, second['run_id'])
        report = self.compare(first, second)
        self.assertEqual(report['results'][0]['change'], 'unrecorded')
        self.assertIsNone(report['results'][0]['current_status'])

    def test_missing_contract_changed_policy_and_definitions_prevent_comparison(self):
        f = self.f
        first = self.complete(TestStatus.PASSED)
        second = self.complete(TestStatus.PASSED)
        for column, value in (('contracts_json', None), ('contracts_json', '{"LOGIN-001":"different"}'),
                              ('configuration_json', '{"base_url":"http://127.0.0.1:8000/","allowed_hosts":["127.0.0.1"],"allow_data_changes":true}')):
            with f.projects._connection() as connection:
                row = connection.execute(f'SELECT {column} FROM dashboard_test_runs WHERE run_id=?', (second['run_id'],)).fetchone()
                connection.execute(f'UPDATE dashboard_test_runs SET {column}=? WHERE run_id=?', (value, second['run_id']))
            report = self.compare(first, second)
            self.assertFalse(report['comparable'])
            self.assertEqual(report['results'], [])
            with f.projects._connection() as connection:
                connection.execute(f'UPDATE dashboard_test_runs SET {column}=? WHERE run_id=?', (row[0], second['run_id']))

    def test_active_self_and_cross_owner_comparisons_are_denied(self):
        f = self.f
        first = self.complete(TestStatus.PASSED)
        second = f.submit()
        for before, after in ((first, first), (first, second)):
            with self.assertRaises(ValueError):
                self.compare(before, after)
        with self.assertRaises(TestRunNotFound):
            compare_runs(f.runs, f.other, f.pid, first['run_id'], second['run_id'])
