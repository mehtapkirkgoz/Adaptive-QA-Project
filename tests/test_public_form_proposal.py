"""Public proposal metadata cannot become local execution or resolve target inputs."""
from dataclasses import replace
import json
import unittest
from unittest.mock import patch

from adaptive_qa.config import ProjectConfig
from adaptive_qa.element_models import ElementMapping, LocatorSpec, LocatorStrategy
from adaptive_qa.interactive_contracts import FormOperation, InteractiveFormContract
from adaptive_qa.local_form_binding import LocalBooleanResponse, decode_local_binding
from adaptive_qa.public_form_proposal import PublicFormProposal, encode_public_proposal, decode_public_proposal
from adaptive_qa.secrets import SecretReference


class PublicFormProposalTests(unittest.TestCase):
    def setUp(self):
        self.form = InteractiveFormContract('a'*32, 'b'*64, FormOperation.SEARCH,
            (SecretReference('OWNED_QUERY'),),
            ElementMapping('search.results', (LocatorSpec(LocatorStrategy.TEST_ID, 'results-ready'),)))
        self.proposal = PublicFormProposal(self.form, 'https://qa.example.test/search',
            'https://qa.example.test/search/execute', ('query',),
            LocalBooleanResponse(200, 'found', True), LocalBooleanResponse(404, 'found', False))
        self.project = ProjectConfig('a'*32, 'Owned proposal', self.proposal.document_url,
                                     ('qa.example.test',), True)

    def test_construction_validation_codec_and_fingerprint_never_resolve_or_connect(self):
        with patch.object(SecretReference, 'resolve', side_effect=AssertionError('No input resolution')), \
                patch('socket.getaddrinfo', side_effect=AssertionError('No DNS')), \
                patch('socket.socket', side_effect=AssertionError('No connection')):
            proposal = replace(self.proposal)
            proposal.validate_project(self.project, current_fingerprint='b'*64)
            data = json.loads(json.dumps(encode_public_proposal(proposal)))
            self.assertEqual(decode_public_proposal(data, self.form), proposal)
            self.assertEqual(len(proposal.fingerprint()), 64)
            self.assertFalse(proposal.execution_authorized)
            self.assertNotIn('OWNED_QUERY', json.dumps(data))

    def test_private_cross_origin_ambiguous_and_noncanonical_urls_are_rejected(self):
        urls = ('http://qa.example.test/search', 'https://other.example.test/search',
            'https://127.0.0.1/search', 'https://10.0.0.1/search', 'https://localhost/search',
            'https://qa.example.test:8443/search', 'https://qa.example.test:443/search',
            'https://user:password@qa.example.test/search', self.proposal.document_url,
            'https://qa.example.test/search?token=value', 'https://qa.example.test/search#result',
            'https://qa.example.test/a/../search', 'https://qa.example.test/a%2fsearch',
            'https://qa.example.test//search', 'https://qa.example.test/search\n',
            'https://qa.example.test', 'https://QA.example.test/search',
            'https://qa.example.test/arama-şimdi')
        with patch('socket.getaddrinfo', side_effect=AssertionError('No DNS')):
            for url in urls:
                with self.subTest(url=url), self.assertRaises(ValueError):
                    replace(self.proposal, endpoint_url=url)

    def test_permission_project_configuration_and_origin_must_match(self):
        changes = (replace(self.project, allow_data_changes=False),
                   replace(self.project, project_id='c'*32),
                   replace(self.project, base_url='https://qa.example.test/other'),
                   replace(self.project, allowed_hosts=('qa.example.test', 'other.example.test')))
        for project in changes:
            with self.assertRaises(ValueError):
                self.proposal.validate_project(project, current_fingerprint='b'*64)
        with self.assertRaises(ValueError):
            self.proposal.validate_project(self.project, current_fingerprint='c'*64)

    def test_operation_specific_fields_and_response_assertions_remain_typed(self):
        for fields in (['query'], (), ('query', 'other'), ('bad&key',), ('a'*41,)):
            with self.assertRaises(ValueError):
                replace(self.proposal, field_names=fields)
        for change in ({'form': None}, {'accepted': {'found': True}},
                       {'rejected': self.proposal.accepted}):
            with self.assertRaises(ValueError):
                replace(self.proposal, **change)
        form = replace(self.form, operation=FormOperation.LOGIN,
            inputs=(SecretReference('OWNED_ACCOUNT'), SecretReference('OWNED_PASSWORD')),
            completion=ElementMapping('login.accepted', (LocatorSpec(LocatorStrategy.TEST_ID, 'signed-in'),)))
        with self.assertRaises(ValueError):
            replace(self.proposal, form=form)
        login = replace(self.proposal, form=form, field_names=('account', 'password'))
        self.assertFalse(login.execution_authorized)

    def test_changed_endpoints_inputs_postconditions_and_responses_change_fingerprint(self):
        variants = (self.proposal,
            replace(self.proposal, endpoint_url='https://qa.example.test/v2/search'),
            replace(self.proposal, field_names=('term',)),
            replace(self.proposal, accepted=LocalBooleanResponse(201, 'found', True)),
            replace(self.proposal, form=replace(self.form, inputs=(SecretReference('OTHER_QUERY'),))),
            replace(self.proposal, form=replace(self.form,
                completion=ElementMapping('search.results', (LocatorSpec(LocatorStrategy.TEST_ID, 'other-result'),)))))
        self.assertEqual(len({item.fingerprint() for item in variants}), len(variants))

    def test_codec_rejects_values_unknown_fields_and_untyped_expectations(self):
        data = json.loads(json.dumps(encode_public_proposal(self.proposal)))
        for change in ({'password': 'plaintext'}, {'execution_authorized': True}, {'method': 'GET'},
                       {'field_names': 'query'}, {'accepted': {**data['accepted'], 'expected_value': 'true'}}):
            with self.assertRaises(ValueError):
                decode_public_proposal({**data, **change}, self.form)
        with self.assertRaises(ValueError):
            decode_local_binding(data, self.form)

    def test_existing_local_gate_and_worker_cannot_execute_a_public_proposal(self):
        from adaptive_qa.interactive_process import run_isolated_local_form
        from adaptive_qa.owned_submission import OwnedSubmissionGate
        with patch.object(SecretReference, 'resolve', side_effect=AssertionError('No values')), \
                patch('socket.getaddrinfo', side_effect=AssertionError('No DNS')), \
                patch('adaptive_qa.interactive_process.subprocess.Popen') as spawn:
            with self.assertRaises(ValueError):
                run_isolated_local_form(self.proposal, self.project, current_fingerprint='b'*64)
            with self.assertRaises(ValueError):
                OwnedSubmissionGate(self.proposal, self.project, current_fingerprint='b'*64)
            spawn.assert_not_called()
