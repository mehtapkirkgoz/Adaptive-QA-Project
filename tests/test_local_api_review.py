"""Review remains offline; confirmation and project drift fail before dispatch."""
from dataclasses import replace
import unittest
from unittest.mock import patch

from adaptive_qa.api_models import ApiCase, ApiRequest, HttpMethod, JsonCheck, JsonOperator
from adaptive_qa.config import ProjectConfig
from adaptive_qa.local_api_review import review_local_api, run_reviewed_local_api
from adaptive_qa.models import TestCase, TestType


class LocalApiReviewTests(unittest.TestCase):
    def setUp(self):
        self.project = ProjectConfig('a'*32, 'Owned API', 'http://127.0.0.1:8000', ('127.0.0.1',), False)
        self.case = ApiCase(TestCase('LOCAL-API-READ', 'Explicit readiness', TestType.API,
            ('api',), ('Read the configured endpoint',), 'Readiness is true'),
            ApiRequest('/different/readiness'), 200,
            (JsonCheck(('available',), JsonOperator.EQUALS, True),))

    def test_review_is_offline_and_assertion_changes_invalidate_confirmation(self):
        with patch('socket.getaddrinfo', side_effect=AssertionError('No DNS')), \
             patch('adaptive_qa.secrets.SecretReference.resolve', side_effect=AssertionError('No secrets')):
            review = review_local_api(self.project, self.case)
        different = review_local_api(self.project, replace(self.case, expected_status=201))
        self.assertNotEqual(review.fingerprint, different.fingerprint)
        with patch('adaptive_qa.api_process.run_isolated_api_case') as child:
            with self.assertRaises(ValueError):
                run_reviewed_local_api(different, self.project, confirmed_fingerprint=review.fingerprint)
            with self.assertRaises(ValueError):
                run_reviewed_local_api(review, replace(self.project, name='Changed'), confirmed_fingerprint=review.fingerprint)
        child.assert_not_called()

    def test_no_external_origin_authentication_query_or_write_authority(self):
        for project in (replace(self.project, base_url='https://example.test', allowed_hosts=('example.test',)),
                        replace(self.project, base_url='http://127.0.0.1:8000/path')):
            with self.assertRaises(ValueError): review_local_api(project, self.case)
        requests = (ApiRequest('/api', use_authentication=True),
                    ApiRequest('/api', query=(('q','input'),)))
        for request in requests:
            with self.assertRaises(ValueError):review_local_api(self.project, replace(self.case, request=request))
        write = replace(self.case, definition=replace(self.case.definition, changes_data=True),
                        request=ApiRequest('/api', HttpMethod.POST))
        with self.assertRaises(ValueError):review_local_api(self.project, write)

    def test_confirmation_dispatches_through_existing_bounded_child(self):
        review = review_local_api(self.project, self.case)
        cancellation = lambda: True
        with patch('adaptive_qa.api_process.run_isolated_api_case', return_value='cancelled') as child:
            self.assertEqual(run_reviewed_local_api(review, self.project,
                confirmed_fingerprint=review.fingerprint, should_cancel=cancellation), 'cancelled')
        self.assertEqual(child.call_args.args[0], self.case)
        self.assertEqual(child.call_args.kwargs, dict(timeout_seconds=15, should_cancel=cancellation))
