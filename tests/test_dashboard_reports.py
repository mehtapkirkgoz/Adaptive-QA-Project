"""Report fidelity, non-execution and ownership boundaries."""

import unittest
from unittest.mock import patch

import test_dashboard_runs as fixtures
from adaptive_qa.dashboard_reports import build_run_report
from adaptive_qa.dashboard_runs import TestRunNotFound
from adaptive_qa.models import TestResult, TestStatus


class DashboardReportTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.DashboardRunsTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def report(self, run, **kwargs):
        f = self.fixture
        return build_run_report(f.runs, f.actor, f.pid, run['run_id'], **kwargs)

    def test_queued_and_cancelled_cases_are_not_invented_results(self):
        f = self.fixture
        run = f.submit()
        for expected in ('queued', 'cancelled'):
            with patch.object(f.runs, 'submit', side_effect=AssertionError('No execution')):
                report = self.report(run)
            self.assertEqual(report['run_status'], expected)
            self.assertEqual(report['requested_total'], 1)
            self.assertEqual(report['unrecorded_total'], 1)
            self.assertEqual(report['recorded_total'], 0)
            self.assertEqual(sum(report['status_counts'].values()), 0)
            f.runs.cancel(f.actor, f.pid, run['run_id'])

    def test_filter_preserves_actual_totals_and_lifecycle(self):
        f = self.fixture
        run = f.submit()
        work = f.runs.claim_next()
        f.runs.record_result(work, TestResult('LOGIN-001', TestStatus.FAILED, .5, 'Private adapter text'))
        f.runs.finish(work)
        report = self.report(run, status='passed')
        self.assertEqual(report['run_status'], 'completed')
        self.assertEqual(report['status_counts']['failed'], 1)
        self.assertEqual(report['recorded_total'], 1)
        self.assertEqual(report['unrecorded_total'], 0)
        self.assertEqual(report['results'], [])
        failed = self.report(run, status='failed')
        self.assertEqual(failed['results'][0]['duration_seconds'], .5)
        self.assertNotIn('Private adapter text', str(failed))
        self.assertGreater(failed['catalog_total'], failed['requested_total'])
        self.assertEqual(failed['catalog_total'], 100)

    def test_other_owner_or_project_cannot_read_report(self):
        f = self.fixture
        run = f.submit()
        second = f.projects.create(f.actor, 'Second')
        for actor, project in ((f.other, f.pid), (f.actor, second.project_id)):
            with self.assertRaises(TestRunNotFound):
                build_run_report(f.runs, actor, project, run['run_id'])

    def test_invalid_filters_are_rejected(self):
        run = self.fixture.submit()
        for status in ('completed', '', 'FAILED', [], True):
            with self.subTest(status=status), self.assertRaises(ValueError):
                self.report(run, status=status)
