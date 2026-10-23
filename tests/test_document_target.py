"""Document bindings cannot grant other cases, destinations or path escapes."""

import unittest
from unittest.mock import patch

from adaptive_qa.document_target import validate_document_path
from adaptive_qa.browser_process import run_isolated_sample_test


class DocumentTargetTests(unittest.TestCase):
    def test_independent_cases_accept_only_canonical_paths(self):
        for case in ('DOC-001', 'DOC-002', 'DOC-003', 'DOC-004', 'DOC-005'):
            self.assertEqual(validate_document_path(case, '/information/page.html'), '/information/page.html')

    def test_path_escapes_and_unrelated_bindings_are_rejected(self):
        for path in ('', None, 1, 'https://example.test/', '//example.test/', '/a/../b', '/a/./b',
                     '/%2e%2e/b', '/a?token=x', '/a#b', '/a\\b', '/a b', '/a\x00', '/a:1', '/'+'x'*512):
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate_document_path('DOC-001', path)
        for case, site in (('LOGIN-001', 'root'), ('API-001', 'root'), ('DOC-001', 'english')):
            with self.assertRaises(ValueError):
                validate_document_path(case, '/page.html', site=site)

    def test_invalid_binding_is_rejected_before_process_creation(self):
        with patch('adaptive_qa.browser_process.subprocess.Popen') as launch:
            with self.assertRaises(ValueError):
                run_isolated_sample_test('LOGIN-001', document_path='/other.html')
            launch.assert_not_called()
