"""Reusable local bindings pin endpoints, input names and exact boolean assertions."""
from dataclasses import replace
import unittest
from unittest.mock import patch
from adaptive_qa.config import ProjectConfig
from adaptive_qa.element_models import ElementMapping,LocatorSpec,LocatorStrategy
from adaptive_qa.interactive_contracts import FormOperation,InteractiveFormContract
from adaptive_qa.local_form_binding import LocalFormBinding,LocalBooleanResponse
from adaptive_qa.owned_submission import OwnedSubmissionGate,CONTENT_TYPE
from adaptive_qa.secrets import SecretReference


class LocalFormBindingTests(unittest.TestCase):
    def setUp(self):
        form=InteractiveFormContract('a'*32,'b'*64,FormOperation.LOGIN,
            (SecretReference('LOCAL_ACCOUNT'),SecretReference('LOCAL_PASSPHRASE')),
            ElementMapping('login.accepted',(LocatorSpec(LocatorStrategy.TEST_ID,'account-ready'),)))
        self.binding=LocalFormBinding(form,'http://127.0.0.1:8000/account/access','http://127.0.0.1:8000/session/check',
            ('account','passphrase'),LocalBooleanResponse(201,'authenticated',True),LocalBooleanResponse(403,'authenticated',False))
        self.project=ProjectConfig('a'*32,'Owned reusable',self.binding.document_url,('127.0.0.1',),True)

    def test_binding_and_gate_never_resolve_inputs_or_connect(self):
        with patch.object(SecretReference,'resolve',side_effect=AssertionError('No values')),patch('socket.socket',side_effect=AssertionError('No socket')):
            gate=OwnedSubmissionGate(self.binding,self.project,current_fingerprint='b'*64)
            self.assertTrue(gate.admit(url=self.binding.endpoint_url,method='POST',content_type=CONTENT_TYPE,body=b'account=fixture&passphrase=example'))
            self.assertEqual(len(self.binding.fingerprint()),64)

    def test_only_exact_owned_normalized_paths_are_allowed(self):
        for url in ('https://example.com/login','http://localhost:8000/account','http://127.0.0.1:8001/account',
                    self.binding.endpoint_url+'?token=x',self.binding.endpoint_url+'#x',
                    'http://127.0.0.1:8000/a/../session','http://127.0.0.1:8000/a%2fsession',
                    'http://127.0.0.1:8000//session','http://user:pass@127.0.0.1:8000/session'):
            with self.subTest(url=url),self.assertRaises(ValueError):replace(self.binding,endpoint_url=url)

    def test_field_and_response_contracts_are_typed_bounded_and_distinct(self):
        for fields in (['account','passphrase'],('account','account'),('account',),('account','bad&key'),('a'*41,'passphrase')):
            with self.assertRaises(ValueError):replace(self.binding,field_names=fields)
        for args in ((True,'authenticated',True),(302,'authenticated',True),(200,'authenticated','true'),(200,'a.b',True)):
            with self.assertRaises(ValueError):LocalBooleanResponse(*args)
        with self.assertRaises(ValueError):replace(self.binding,rejected=self.binding.accepted)

    def test_response_parser_rejects_echoes_duplicates_strings_and_unexpected_codes(self):
        self.assertEqual(self.binding.classify_response(201,b'{"authenticated":true}'),'accepted')
        self.assertEqual(self.binding.classify_response(403,b'{"authenticated":false}'),'rejected')
        for status,body in ((201,b'{"authenticated":"true"}'),(201,b'{"authenticated":1}'),
                (201,b'{"authenticated":true,"password":"echo"}'),(201,b'{"authenticated":false,"authenticated":true}'),
                (200,b'{"authenticated":true}'),(302,b'{"authenticated":true}'),(201,b'x'*1025),(201,b'null')):
            self.assertIsNone(self.binding.classify_response(status,body))

    def test_changes_to_endpoint_fields_or_assertion_change_digest(self):
        bindings=(self.binding,replace(self.binding,endpoint_url='http://127.0.0.1:8000/v2/session'),
            replace(self.binding,field_names=('email','code')),replace(self.binding,accepted=LocalBooleanResponse(200,'signedIn',True)))
        self.assertEqual(len({item.fingerprint() for item in bindings}),4)
        for project,fingerprint in ((replace(self.project,allow_data_changes=False),'b'*64),(self.project,'c'*64),
                (replace(self.project,base_url='http://127.0.0.1:8000/other'),'b'*64)):
            with self.assertRaises(ValueError):self.binding.validate_project(project,current_fingerprint=fingerprint)
