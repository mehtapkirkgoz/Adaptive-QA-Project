"""Document bindings cannot grant other cases, destinations or path escapes."""

import unittest
from unittest.mock import patch

from adaptive_qa.document_target import validate_document_path, controlled_start_path, serialize_target_binding, validate_runtime_binding
from adaptive_qa.browser_process import run_isolated_sample_test


class DocumentTargetTests(unittest.TestCase):
    def test_discovered_document_binding_requires_exact_saved_path_and_case_family(self):
        settings = {'base_url': 'http://127.0.0.1:8000/information.html', 'allowed_hosts': ['127.0.0.1']}
        binding = serialize_target_binding('DOC-001', settings['base_url'])
        self.assertEqual(binding, {'target_binding': 'local_document', 'document_path': '/information.html'})
        decision = dict(binding, decision='selected', test_type='ui')
        validate_runtime_binding(settings, 'DOC-001', decision)
        for case, changed in (('LOGIN-001', decision), ('DOC-001', dict(decision, document_path='/other.html')),
                              ('DOC-001', dict(decision, target_binding='local_root')),
                              ('DOC-001', dict(decision, decision='blocked'))):
            with self.subTest(case=case, changed=changed), self.assertRaises(ValueError):
                validate_runtime_binding(settings, case, changed)
        self.assertEqual(serialize_target_binding('LOGIN-001', settings['base_url']), {'target_binding': None})

    def test_controlled_start_path_cannot_change_origin_or_bypass_host_scope(self):
        for url in ('https://example.test/', 'http://127.0.0.1:8001/a',
                    'http://127.0.0.1:8000@evil.test/a', 'http://127.0.0.1:8000//evil.test/a',
                    'http://127.0.0.1:8000/a?token=x', 'http://127.0.0.1:8000/%2e%2e/a'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                controlled_start_path({'base_url': url, 'allowed_hosts': ['127.0.0.1']})
        with self.assertRaises(ValueError):
            controlled_start_path({'base_url': 'http://127.0.0.1:8000/a', 'allowed_hosts': []})
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
