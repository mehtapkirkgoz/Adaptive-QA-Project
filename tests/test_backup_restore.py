"""Real application recovery with session revocation and no queued execution."""

from contextlib import closing, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from adaptive_qa.auth_store import AuthStore, AuthenticationError
from adaptive_qa.__main__ import main
from adaptive_qa.backup import create_backup
from adaptive_qa.backup_restore import prepare_restore
from adaptive_qa.dashboard_runs import DashboardRunQueue
from adaptive_qa.deployment import DeploymentPlan, Environment
from adaptive_qa.project_store import ProjectStore


class BackupRestoreTests(unittest.TestCase):
    def test_shared_run_restore_keeps_partial_results_and_png_but_cancels_claims(self):
        from adaptive_qa.organization_store import OrganizationStore
        from adaptive_qa.organization_projects import OrganizationProjects
        from adaptive_qa.organization_discovery import OrganizationDiscoveryQueue
        from adaptive_qa.organization_runs import OrganizationRunQueue
        from adaptive_qa.dashboard_worker import configuration_fingerprint
        from adaptive_qa.models import TestResult, TestStatus
        from png_fixture import png_bytes
        actor = self.grant.actor
        organizations = OrganizationStore(self.projects)
        organization = organizations.create(actor, 'Shared recovery')
        scoped = OrganizationProjects(organizations)
        project = scoped.create(actor, organization, 'Fixture')['project_id']
        scoped.save_configuration(actor, organization, project, {'base_url':'http://127.0.0.1:8000/',
            'allowed_hosts':['127.0.0.1'],'allow_data_changes':False,'secret_references':{}})
        discovery = OrganizationDiscoveryQueue(scoped)
        job = discovery.submit(actor,organization,project)['job_id']
        work = discovery.claim_next()
        discovery.finish(work,report={'project_id':project,'execution_authorized':False,
            'discovery_status':'completed','inspected_pages':1,
            'configuration_fingerprint':configuration_fingerprint(work.configuration),
            'cases':[{'case_id':case,'decision':'selected','test_type':'ui','target_binding':'local_root'}
                     for case in ('LOGIN-001','SEARCH-001')]})
        runs = OrganizationRunQueue(discovery)
        run = runs.submit(actor,organization,project,job,('LOGIN-001','SEARCH-001'))
        claim = runs.claim_next()
        runs.record_result(claim,TestResult('LOGIN-001',TestStatus.PASSED,.1,'Fixture'),evidence_png=png_bytes())
        runs.submit(actor,organization,project,job,('LOGIN-001',))
        bundle = create_backup(self.plan,maintenance_confirmed=True)['bundle_id']
        before = self.projects.database.read_bytes()
        result = prepare_restore(self.plan,bundle,maintenance_confirmed=True)
        database = self.plan.directory/'recovery'/result['recovery_id']/'projects.sqlite'
        recovered = OrganizationRunQueue(OrganizationDiscoveryQueue(OrganizationProjects(OrganizationStore(ProjectStore(database)))))
        public = recovered.get(actor,organization,project,run['run_id'])
        self.assertEqual(public['status'],'cancelled')
        self.assertEqual(len(public['results']),1)
        evidence_id = public['results'][0]['evidence_id']
        self.assertEqual(recovered.evidence(actor,organization,project,run['run_id'],evidence_id),png_bytes())
        with self.assertRaises(ValueError):
            recovered.finish(claim)
        self.assertIsNone(recovered.claim_next())
        self.assertEqual(before,self.projects.database.read_bytes())

    def test_organization_jobs_and_reservations_are_cancelled_only_in_recovered_copy(self):
        from adaptive_qa.organization_store import OrganizationStore
        from adaptive_qa.organization_projects import OrganizationProjects
        from adaptive_qa.organization_discovery import OrganizationDiscoveryQueue
        from adaptive_qa.organization_admission import OrganizationAdmission
        actor = self.grant.actor
        organizations = OrganizationStore(self.projects)
        organization = organizations.create(actor, 'Recovery fixture')
        scoped = OrganizationProjects(organizations)
        project = scoped.create(actor, organization, 'Shared')['project_id']
        scoped.save_configuration(actor, organization, project, {'base_url': 'http://127.0.0.1:8000/',
            'allowed_hosts': ['127.0.0.1'], 'allow_data_changes': False, 'secret_references': {}})
        queue = OrganizationDiscoveryQueue(scoped)
        queue.submit(actor, organization, project)
        queue.claim_next()
        queue.submit(actor, organization, project)
        ledger = OrganizationAdmission(organizations)
        reservation = ledger.reserve(actor, organization)
        ledger.claim(actor, organization, reservation)
        ledger.reserve(actor, organization)
        bundle = create_backup(self.plan, maintenance_confirmed=True)['bundle_id']
        original = self.projects.database.read_bytes()
        result = prepare_restore(self.plan, bundle, maintenance_confirmed=True)
        recovered = self.plan.directory/'recovery'/result['recovery_id']/'projects.sqlite'
        with closing(sqlite3.connect(recovered)) as c:
            for table in ('dashboard_organization_discovery', 'dashboard_organization_admissions'):
                self.assertEqual(c.execute(f'SELECT status, claim_token FROM {table}').fetchall(),
                                 [('cancelled', None), ('cancelled', None)])
            self.assertEqual(c.execute('SELECT count(*) FROM dashboard_organization_projects').fetchone()[0], 1)
        self.assertEqual(self.projects.database.read_bytes(), original)

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.plan = DeploymentPlan(Environment.STAGING, Path(self.temp.name), 'https://qa.example.test')
        self.auth = AuthStore(self.plan.directory / 'auth.sqlite')
        actor = self.auth.create_user('owner@example.test', 'fixture password only')
        self.grant = self.auth.login('owner@example.test', 'fixture password only')
        self.projects = ProjectStore(self.plan.directory / 'projects.sqlite')
        self.project = self.projects.create(actor, 'Original fixture project')
        DashboardRunQueue(self.projects)
        with self.projects._connection() as connection:
            for index, status in enumerate(('queued', 'running', 'cancel_requested', 'completed')):
                connection.execute('INSERT INTO dashboard_discovery_jobs '
                    '(job_id, project_id, owner_id, status, configuration_json, claim_token) '
                    'VALUES (?, ?, ?, ?, ?, ?)',
                    (f'{index:032x}', self.project.project_id, actor.user_id, status, '{}', 'old claim'))
                connection.execute('INSERT INTO dashboard_test_runs '
                    '(run_id, project_id, owner_id, discovery_job_id, case_ids_json, '
                    'configuration_json, status, claim_token) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                    (f'{index:032x}', self.project.project_id, actor.user_id, f'{index:032x}',
                     '[]', '{}', status, 'old claim'))
        self.bundle_id = create_backup(self.plan, maintenance_confirmed=True)['bundle_id']

    def test_restore_revokes_old_sessions_cancels_work_and_preserves_live_and_backup_bytes(self):
        before = {path.relative_to(self.plan.directory): path.read_bytes()
                  for path in self.plan.directory.rglob('*') if path.is_file()}
        with patch('socket.socket', side_effect=AssertionError('No network')), \
                patch('subprocess.Popen', side_effect=AssertionError('No execution')):
            result = prepare_restore(self.plan, self.bundle_id, maintenance_confirmed=True)
        recovery = self.plan.directory / 'recovery' / result['recovery_id']
        self.assertFalse(result['activation_enabled'])
        for relative, data in before.items():
            self.assertEqual((self.plan.directory / relative).read_bytes(), data)
        token = self.grant.token.value
        self.assertIsNotNone(self.auth.actor_for_session(token))
        recovered_auth = AuthStore(recovery / 'auth.sqlite')
        with self.assertRaises(AuthenticationError):
            recovered_auth.actor_for_session(token)
        self.assertIsNotNone(recovered_auth.login('owner@example.test', 'fixture password only'))
        with closing(sqlite3.connect(recovery / 'projects.sqlite')) as connection:
            self.assertEqual(connection.execute('SELECT name FROM dashboard_projects').fetchone()[0],
                             'Original fixture project')
            for table in ('dashboard_test_runs', 'dashboard_discovery_jobs'):
                rows = connection.execute(f'SELECT status, claim_token FROM {table} ORDER BY sequence').fetchall()
                self.assertEqual(rows[:3], [('cancelled', None)] * 3)
                self.assertEqual(rows[3][0], 'completed')
        metadata = json.loads((recovery / 'recovery.json').read_text())
        self.assertTrue(metadata['sessions_invalidated'])
        self.assertTrue(metadata['pending_work_cancelled'])

    def test_confirmation_is_required_and_live_storage_is_never_the_target(self):
        with self.assertRaises(ValueError):
            prepare_restore(self.plan, self.bundle_id)
        self.assertFalse((self.plan.directory / 'recovery').exists())
        first = prepare_restore(self.plan, self.bundle_id, maintenance_confirmed=True)
        output = StringIO()
        with patch('sys.argv', ['adaptive-qa', 'deployment', 'prepare-restore', '--environment', 'staging',
                '--data-root', str(self.plan.data_root), '--origin', self.plan.public_origin,
                '--bundle-id', self.bundle_id, '--offline-maintenance']), redirect_stdout(output):
            main()
        second = json.loads(output.getvalue())
        self.assertNotEqual(first['recovery_id'], second['recovery_id'])

    def test_unsupported_application_schema_never_publishes_a_recovery(self):
        with closing(sqlite3.connect(self.plan.directory / 'auth.sqlite')) as connection:
            connection.execute('DROP TABLE dashboard_sessions')
            connection.commit()
        bundle_id = create_backup(self.plan, maintenance_confirmed=True)['bundle_id']
        with self.assertRaisesRegex(ValueError, 'schema'):
            prepare_restore(self.plan, bundle_id, maintenance_confirmed=True)
        self.assertEqual(list((self.plan.directory / 'recovery').iterdir()), [])

    def test_copy_deadline_cleans_partial_recovery(self):
        with patch('adaptive_qa.backup_restore.monotonic', side_effect=[0, 11]):
            with self.assertRaisesRegex(ValueError, 'budget'):
                prepare_restore(self.plan, self.bundle_id, maintenance_confirmed=True)
        self.assertEqual(list((self.plan.directory / 'recovery').iterdir()), [])
