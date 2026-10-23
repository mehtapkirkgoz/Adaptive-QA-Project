"""Real storage: expired work cleanup, live lease preservation and bounded pruning."""

from argparse import Namespace
from pathlib import Path
import json
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import test_organization_runs as fixtures
from adaptive_qa.agent_broker import AgentBroker
from adaptive_qa.agent_registry import AgentRegistry
from adaptive_qa.dashboard_cli import run
from adaptive_qa.maintenance import maintenance_once
from adaptive_qa.worker_lock import worker_lock
from png_fixture import png_bytes


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.OrganizationRunTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.registry = AgentRegistry(self.f.scoped, clock=lambda: self.f.now)
        grant = self.registry.issue(self.f.owner, self.f.org, self.f.project)
        self.identity = self.registry.authenticate(grant.agent_id, grant.token.value, 1)
        self.broker = AgentBroker(self.registry, self.f.queue)

    def maintain(self, **kwargs):
        with patch('socket.socket', side_effect=AssertionError('Maintenance must not connect')), \
                patch('subprocess.Popen', side_effect=AssertionError('Maintenance must not dispatch')):
            return maintenance_once(self.f.projects, clock=lambda: self.f.now, **kwargs)

    def test_expired_agent_releases_capacity_preserves_outcomes_and_never_replays(self):
        run = self.f.submit(cases=('LOGIN-001', 'SEARCH-001'))
        lease = self.broker.claim(self.identity)
        self.broker.result(self.identity, lease['lease_id'], 'LOGIN-001', 'passed', .1, png=png_bytes())
        self.f.now += 121
        self.assertEqual(self.maintain(), {'cancelled_agent_runs': 1, 'personal_evidence_removed': 0, 'shared_evidence_removed': 1})
        saved = self.f.queue.get(self.f.owner, self.f.org, self.f.project, run['run_id'])
        self.assertEqual(saved['status'], 'cancelled')
        self.assertEqual([row['case_id'] for row in saved['results']], ['LOGIN-001'])
        self.assertEqual(self.f.queue.admission.usage(self.f.owner, self.f.org)['active_runs'], 0)
        self.assertEqual(self.maintain()['cancelled_agent_runs'], 0)
        self.assertIsNone(self.broker.claim(self.identity))

    def test_live_agent_lease_and_active_capacity_remain_intact(self):
        run = self.f.submit()
        self.broker.claim(self.identity)
        self.assertEqual(self.maintain()['cancelled_agent_runs'], 0)
        self.assertEqual(self.f.queue.get(self.f.owner, self.f.org, self.f.project, run['run_id'])['status'], 'running')
        self.assertEqual(self.f.queue.admission.usage(self.f.owner, self.f.org)['active_runs'], 1)

    def test_evidence_batches_are_bounded_and_results_remain_recorded(self):
        run = self.f.submit(cases=('LOGIN-001', 'SEARCH-001'))
        work = self.f.queue.claim_next()
        for case in ('LOGIN-001', 'SEARCH-001'):
            self.f.queue.record_result(work, self.f.result(case), evidence_png=png_bytes())
        self.f.queue.finish(work)
        self.f.now += 61
        self.assertEqual(self.maintain(limit=1)['shared_evidence_removed'], 1)
        self.assertEqual(self.maintain(limit=1)['shared_evidence_removed'], 1)
        self.assertEqual(self.maintain(limit=1)['shared_evidence_removed'], 0)
        saved = self.f.queue.get(self.f.owner, self.f.org, self.f.project, run['run_id'])
        self.assertEqual(saved['status'], 'completed')
        self.assertEqual(len(saved['results']), 2)

    def test_worker_lock_excludes_maintenance(self):
        with worker_lock(self.f.projects.database), self.assertRaises(ValueError):
            self.maintain()

    def test_cli_invalid_limit_does_not_create_a_database(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary)/'absent.sqlite'
            for limit in (True, 0, 101, -1):
                with self.assertRaises(ValueError):
                    run(Namespace(dashboard_command='maintenance-once', database=path, limit=limit))
            self.assertFalse(path.exists())

    def test_real_cli_reports_counts_without_credentials_or_private_identifiers(self):
        self.f.submit()
        lease = self.broker.claim(self.identity)
        # The fixture clock is historical, so the real CLI sees an expired lease.
        result = subprocess.run([sys.executable, '-m', 'adaptive_qa', 'dashboard', 'maintenance-once',
            '--database', str(self.f.projects.database), '--limit', '1'],
            capture_output=True, text=True, timeout=15, check=True)
        self.assertEqual(json.loads(result.stdout), {'cancelled_agent_runs': 1,
            'personal_evidence_removed': 0, 'shared_evidence_removed': 0})
        self.assertNotIn(lease['lease_id'], result.stdout + result.stderr)
        self.assertNotIn(str(self.f.projects.database), result.stdout + result.stderr)
