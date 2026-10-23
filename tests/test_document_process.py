"""Configured document dispatch guards and real owned-child lifecycle checks."""

from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import monotonic
import unittest
from unittest.mock import patch

from adaptive_qa.config import ProjectConfig
from adaptive_qa.document_process import run_isolated_document_test
from adaptive_qa.models import TestStatus


class DocumentProcessTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = ProjectConfig('document', 'Document', 'https://qa.example.test/', ('qa.example.test',))

    def run_case(self, **kwargs):
        return run_isolated_document_test('DOC-001', self.project, evidence_directory=self.root, **kwargs)

    def test_invalid_case_target_and_deadline_never_start_a_process(self):
        with patch('adaptive_qa.document_process.subprocess.Popen') as spawn:
            with self.assertRaises(ValueError):
                run_isolated_document_test('LOGIN-001', self.project, evidence_directory=self.root)
            for url in ('http://qa.example.test/', 'https://127.0.0.1/', 'https://qa.example.test:8443/'):
                project = ProjectConfig('doc', 'Doc', url, ('qa.example.test', '127.0.0.1'))
                with self.assertRaises(ValueError):
                    run_isolated_document_test('DOC-001', project, evidence_directory=self.root)
            for timeout in (True, 0, 121, float('nan')):
                with self.assertRaises(ValueError):
                    self.run_case(timeout_seconds=timeout)
            spawn.assert_not_called()

    def test_precancel_never_spawns_or_resolves_dns(self):
        with patch('socket.getaddrinfo', side_effect=AssertionError('No DNS')), \
                patch('adaptive_qa.document_process.subprocess.Popen') as spawn:
            self.assertEqual(self.run_case(should_cancel=lambda: True).status, TestStatus.CANCELLED)
            spawn.assert_not_called()

    def owned_child(self, mode):
        original = subprocess.Popen
        children = []
        started = monotonic()
        def spawn(command, **options):
            if 'adaptive_qa.document_process' not in command:
                return original(command, **options)
            child = original([sys.executable, '-c', 'import time;time.sleep(60)'], **options)
            children.append(child)
            self.assertNotIn(self.project.base_url, command)
            return child
        def cancel():
            if children and mode == 'broken':
                raise RuntimeError('Cancellation source failed')
            return mode == 'cancel' and monotonic()-started > 0.2
        try:
            with patch('adaptive_qa.document_process.subprocess.Popen', side_effect=spawn):
                if mode == 'broken':
                    with self.assertRaisesRegex(RuntimeError, 'Cancellation source'):
                        self.run_case(timeout_seconds=0.5, should_cancel=cancel)
                else:
                    result = self.run_case(timeout_seconds=0.5, should_cancel=cancel)
                    self.assertEqual(result.status, TestStatus.CANCELLED if mode == 'cancel' else TestStatus.ERROR)
                    self.assertEqual(result.evidence_paths, ())
        finally:
            for child in children:
                survived = child.poll() is None
                if survived:
                    child.kill(); child.wait(timeout=5)
                self.assertFalse(survived, 'Owned child survived supervisor exit')

    def test_deadline_terminates_owned_child(self):
        self.owned_child('deadline')

    def test_cancellation_terminates_owned_child(self):
        self.owned_child('cancel')

    def test_callback_exception_terminates_owned_child(self):
        self.owned_child('broken')
