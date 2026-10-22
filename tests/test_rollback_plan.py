"""Rollback compatibility is declarative and never executes a candidate."""

from contextlib import closing, redirect_stdout
import hashlib
from io import StringIO
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from adaptive_qa.__main__ import main
from adaptive_qa.deployment import DeploymentPlan, Environment
from adaptive_qa.rollback_plan import plan_rollback


class RollbackPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plan = DeploymentPlan(Environment.STAGING, self.root, 'https://qa.example.test')
        self.plan.directory.mkdir()
        for name in ('auth.sqlite', 'projects.sqlite'):
            with closing(sqlite3.connect(self.plan.directory / name)) as connection:
                connection.execute('CREATE TABLE sample(value TEXT)')
                connection.execute('PRAGMA user_version=1')
        self.candidate = self.root / 'candidate'
        self.candidate.mkdir()
        files = []
        for name in ('adaptive_qa-0.1.0.whl', 'dashboard.zip', 'requirements.lock.txt', 'frontend-package-lock.json'):
            path = self.candidate / name
            path.write_bytes(b'declarative fixture, never execute')
            files.append({'name': name, 'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        self.manifest = {'schema_version': 1, 'source_commit': 'a' * 40, 'activation_enabled': False,
                         'database_schema_revisions': [0, 1], 'files': files}
        self.write_manifest()

    def write_manifest(self):
        (self.candidate / 'release.json').write_text(json.dumps(self.manifest), encoding='utf-8')

    def run_plan(self):
        return plan_rollback(self.plan, self.candidate, 'a' * 40, maintenance_confirmed=True)

    def test_cli_plan_matches_revisions_without_execution_or_file_mutations(self):
        before = {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
        output = StringIO()
        with patch('socket.socket', side_effect=AssertionError('No network')), \
                patch('subprocess.Popen', side_effect=AssertionError('No candidate execution')), \
                patch('sys.argv', ['adaptive-qa', 'deployment', 'rollback-plan', '--environment', 'staging',
                    '--data-root', str(self.root), '--origin', self.plan.public_origin,
                    '--candidate', str(self.candidate), '--candidate-commit', 'a' * 40, '--offline-maintenance']), \
                redirect_stdout(output):
            main()
        result = json.loads(output.getvalue())
        self.assertTrue(result['schema_compatible'])
        self.assertFalse(result['activation_enabled'])
        self.assertEqual(before, {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob('*') if path.is_file()})

    def test_missing_or_mismatched_support_is_blocked_without_guessing_a_downgrade(self):
        for supported in (None, [0]):
            self.manifest['database_schema_revisions'] = supported
            self.write_manifest()
            self.assertFalse(self.run_plan()['schema_compatible'])

    def test_candidate_tampering_or_wrong_commit_is_rejected(self):
        self.manifest['source_commit'] = 'b' * 40
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, 'identity'):
            self.run_plan()
        self.manifest['source_commit'] = 'a' * 40
        self.write_manifest()
        (self.candidate / 'dashboard.zip').write_bytes(b'modified')
        with self.assertRaises(ValueError):
            self.run_plan()

    def test_offline_confirmation_and_checkpointed_databases_are_required(self):
        with self.assertRaises(ValueError):
            plan_rollback(self.plan, self.candidate, 'a' * 40)
        (self.plan.directory / 'projects.sqlite-wal').write_bytes(b'not checkpointed')
        with self.assertRaisesRegex(ValueError, 'checkpointed'):
            self.run_plan()
