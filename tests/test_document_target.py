"""Document bindings cannot grant other cases, destinations or path escapes."""

import unittest
from unittest.mock import patch

from adaptive_qa.document_target import validate_document_path, controlled_start_path, serialize_target_binding, validate_runtime_binding
from adaptive_qa.browser_process import run_isolated_sample_test


class DocumentTargetTests(unittest.TestCase):
    def test_empty_public_root_path_matches_browser_root_without_widening_scope(self):
        from adaptive_qa.discovery_target import configured_discovery
        for saved in ('https://qa.example.test','https://qa.example.test/'):
            settings=dict(base_url=saved,allowed_hosts=['qa.example.test'],allow_data_changes=False)
            profile,project=configured_discovery(settings)
            self.assertEqual(project.base_url,'https://qa.example.test/')
            self.assertEqual(settings['base_url'],saved,'Saved owner settings stay unchanged')
            for case in ('DOC-001','LOGIN-001'):
                binding=serialize_target_binding(case,saved)
                self.assertEqual(binding['document_url'],'https://qa.example.test/')
                decision=dict(binding,decision='selected',test_type='ui')
                validate_runtime_binding(settings,case,decision)
                for other in ('https://other.example.test/','https://qa.example.test/other',
                              'https://qa.example.test//','https://qa.example.test/%2f',
                              'https://qa.example.test/?x=1','https://qa.example.test/#x',
                              'https://qa.example.test:8443/'):
                    with self.subTest(other=other),self.assertRaises(ValueError):
                        validate_runtime_binding(settings,case,dict(decision,document_url=other))

    def test_root_canonicalization_does_not_rewrite_nonroot_or_ambiguous_urls(self):
        from adaptive_qa.document_url import canonical_root_url
        for url in ('https://example.test/path','https://example.test/path/',
                    'https://example.test?','https://example.test#','https://example.test/%2f',
                    'https://example.test//','https://example.test/a/../b'):
            self.assertEqual(canonical_root_url(url),url)
        self.assertIsNone(canonical_root_url(None))

    def test_discovered_document_binding_requires_exact_saved_path_and_case_family(self):
        settings = {'base_url': 'http://127.0.0.1:8000/information.html', 'allowed_hosts': ['127.0.0.1'], 'allow_data_changes': False}
        binding = serialize_target_binding('DOC-001', settings['base_url'])
        self.assertEqual(binding, {'target_binding': 'local_document', 'document_path': '/information.html'})
        decision = dict(binding, decision='selected', test_type='ui')
        validate_runtime_binding(settings, 'DOC-001', decision)
        for case, changed in (('LOGIN-001', decision), ('DOC-001', dict(decision, document_path='/other.html')),
                              ('DOC-001', dict(decision, target_binding='local_root')),
                              ('DOC-001', dict(decision, decision='blocked'))):
            with self.subTest(case=case, changed=changed), self.assertRaises(ValueError):
                validate_runtime_binding(settings, case, changed)
        self.assertEqual(serialize_target_binding('LOGIN-001', settings['base_url']),
                         {'target_binding': 'local_form', 'document_path': '/information.html'})

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

    def test_public_document_binding_requires_exact_saved_url_and_independent_case(self):
        settings = {'base_url': 'https://qa.example.test/information',
                    'allowed_hosts': ['qa.example.test'], 'allow_data_changes': False}
        binding = serialize_target_binding('DOC-001', settings['base_url'])
        self.assertEqual(binding['target_binding'], 'public_document')
        decision = dict(binding, decision='selected', test_type='ui')
        validate_runtime_binding(settings, 'DOC-001', decision)
        for case, changed in (('LOGIN-001', decision),
                ('DOC-001', dict(decision, document_url='https://qa.example.test/other')),
                ('DOC-001', dict(decision, document_url='https://other.example.test/information')),
                ('DOC-001', dict(decision, target_binding='local_root')),
                ('DOC-001', dict(decision, test_type='api'))):
            with self.subTest(case=case, changed=changed), self.assertRaises(ValueError):
                validate_runtime_binding(settings, case, changed)
        for url in ('https://127.0.0.1/', 'http://qa.example.test/', 'https://qa.example.test:8443/'):
            self.assertIsNone(serialize_target_binding('DOC-001', url)['target_binding'])

    def test_read_only_forms_require_matching_case_family_and_exact_saved_document(self):
        for url, binding_name in (('http://127.0.0.1:8000/account', 'local_form'),
                                  ('https://qa.example.test/account', 'public_form')):
            settings = {'base_url': url, 'allowed_hosts': ['127.0.0.1', 'qa.example.test'], 'allow_data_changes': False}
            binding = serialize_target_binding('LOGIN-001', url)
            self.assertEqual(binding['target_binding'], binding_name)
            decision = dict(binding, decision='selected', test_type='ui')
            validate_runtime_binding(settings, 'LOGIN-001', decision)
            with self.assertRaises(ValueError):
                validate_runtime_binding(settings, 'LOGIN-002', decision)
            with self.assertRaises(ValueError):
                validate_runtime_binding(dict(settings, base_url=url+'/other'), 'LOGIN-001', decision)
            with self.assertRaises(ValueError):
                validate_runtime_binding(settings, 'DOC-001', decision)
