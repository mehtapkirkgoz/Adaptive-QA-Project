"""Expiry is enforced on access, projection and bounded physical cleanup."""

import json
from pathlib import Path
import unittest
from unittest.mock import patch
import test_dashboard_runs as fixtures
from adaptive_qa.dashboard_runs import DashboardRunQueue, TestRunNotFound
from adaptive_qa.dashboard_run_worker import process_run_once
from adaptive_qa.models import TestResult, TestStatus
from png_fixture import png_bytes


class EvidenceRetentionTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.DashboardRunsTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.now = 1000
        self.queue = DashboardRunQueue(self.f.projects, clock=lambda: self.now, retention_seconds=60)

    def capture(self):
        run = self.f.submit()
        work = self.queue.claim_next()
        self.queue.record_result(work, TestResult('LOGIN-001', TestStatus.FAILED, .1, 'private'), evidence_png=png_bytes())
        self.queue.finish(work)
        result = self.queue.get(self.f.actor, self.f.pid, run['run_id'])['results'][0]
        return run['run_id'], result['evidence_id']

    def test_expiry_hides_links_and_denies_bytes_before_cleanup(self):
        rid, eid = self.capture()
        self.assertEqual(self.queue.evidence(self.f.actor, self.f.pid, rid, eid), png_bytes())
        self.now = 1060
        with self.assertRaises(TestRunNotFound):
            self.queue.evidence(self.f.actor, self.f.pid, rid, eid)
        result = self.queue.get(self.f.actor, self.f.pid, rid)['results'][0]
        self.assertTrue(result['evidence_expired'])
        self.assertNotIn('evidence_id', result)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(self.queue.prune_expired_evidence(), {'removed': 1})
        self.assertEqual(self.queue.prune_expired_evidence(), {'removed': 0})
        self.assertEqual(self.queue.get(self.f.actor, self.f.pid, rid)['results'][0], result)

    def test_prune_is_bounded_and_preserves_unexpired_evidence_and_results(self):
        first, _ = self.capture()
        self.now = 1030
        second, eid = self.capture()
        self.now = 1060
        self.assertEqual(self.queue.prune_expired_evidence(limit=1), {'removed': 1})
        self.assertEqual(self.queue.evidence(self.f.actor, self.f.pid, second, eid), png_bytes())
        self.assertEqual(len(self.queue.get(self.f.actor, self.f.pid, first)['results']), 1)

    def test_legacy_unknown_age_is_unavailable_and_prunable(self):
        rid, eid = self.capture()
        with self.f.projects._connection() as connection:
            connection.execute('UPDATE dashboard_run_evidence SET expires_at=NULL WHERE evidence_id=?', (eid,))
            raw = json.loads(connection.execute('SELECT results_json FROM dashboard_test_runs WHERE run_id=?', (rid,)).fetchone()[0])
            raw[0].pop('evidence_expires_at')
            connection.execute('UPDATE dashboard_test_runs SET results_json=? WHERE run_id=?', (json.dumps(raw), rid))
        with self.assertRaises(TestRunNotFound):
            self.queue.evidence(self.f.actor, self.f.pid, rid, eid)
        self.assertTrue(self.queue.get(self.f.actor, self.f.pid, rid)['results'][0]['evidence_expired'])
        self.assertEqual(self.queue.prune_expired_evidence(), {'removed': 1})

    def test_worker_temporary_png_is_removed_after_persisting_owned_copy(self):
        self.f.submit()
        paths = []
        def execute(case_id, **kwargs):
            directory = kwargs['evidence_directory']
            paths.append(directory)
            path = directory / ('a' * 32 + '.png')
            path.write_bytes(png_bytes())
            return TestResult(case_id, TestStatus.PASSED, .1, 'x', (str(path),))
        with patch('adaptive_qa.dashboard_run_worker.run_isolated_sample_test', side_effect=execute):
            run = process_run_once(self.queue)
        self.assertFalse(paths[0].exists())
        result = self.queue.get(self.f.actor, self.f.pid, run['run_id'])['results'][0]
        self.assertEqual(self.queue.evidence(self.f.actor, self.f.pid, run['run_id'], result['evidence_id']), png_bytes())

    def test_retention_and_cleanup_parameters_are_bounded(self):
        for invalid in (0, True, 59, 2592001):
            with self.assertRaises(ValueError):
                DashboardRunQueue(self.f.projects, retention_seconds=invalid)
        for invalid in (0, True, 1001, '10'):
            with self.assertRaises(ValueError):
                self.queue.prune_expired_evidence(limit=invalid)

    def test_worker_failure_cleans_temporary_data_without_deleting_external_files(self):
        self.f.submit()
        directories = []
        external = Path(self.f.temp.name) / 'operator-file.png'
        external.write_bytes(png_bytes())
        def execute(case_id, **kwargs):
            directories.append(kwargs['evidence_directory'])
            (directories[-1] / ('a' * 32 + '.png')).write_bytes(png_bytes())
            raise RuntimeError('Simulated adapter crash')
        with patch('adaptive_qa.dashboard_run_worker.run_isolated_sample_test', side_effect=execute):
            run = process_run_once(self.queue)
        self.assertEqual(run['status'], 'error')
        self.assertFalse(directories[0].exists())
        self.assertEqual(external.read_bytes(), png_bytes())
