"""Owned endpoint admission cannot expand scope, leak values or retry a request."""
from dataclasses import replace
import socket
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

from adaptive_qa.config import ProjectConfig
from adaptive_qa.element_models import ElementMapping, LocatorSpec, LocatorStrategy
from adaptive_qa.interactive_contracts import FormOperation, InteractiveFormContract
from adaptive_qa.owned_submission import OwnedSubmissionContract, OwnedSubmissionGate, CONTENT_TYPE, ORIGIN
from adaptive_qa.secrets import SecretReference


class OwnedSubmissionTests(unittest.TestCase):
    def setUp(self):
        form = InteractiveFormContract("a"*32, "b"*64, FormOperation.LOGIN,
            (SecretReference("FIXTURE_USER"), SecretReference("FIXTURE_PASSWORD")),
            ElementMapping("login.accepted", (LocatorSpec(LocatorStrategy.TEST_ID, "result"),)))
        self.contract = OwnedSubmissionContract(form, "login-transition",
            ORIGIN+"/interactive/login-transition", ORIGIN+"/interactive-submit/login-transition", ("user", "password"))
        self.project = ProjectConfig("a"*32, "Owned fixture", self.contract.document_url, ("127.0.0.1",), True)

    def gate(self):
        return OwnedSubmissionGate(self.contract, self.project, current_fingerprint="b"*64)

    def request(self, **changes):
        return dict(url=self.contract.endpoint_url, method="POST", content_type=CONTENT_TYPE,
                    body=b"user=fixture-user&password=private-canary", **changes)

    def test_valid_body_is_one_shot_without_secret_resolution_or_networking(self):
        with patch.object(SecretReference, "resolve", side_effect=AssertionError("No secret resolution")), patch.object(
                socket, "socket", side_effect=AssertionError("No connection")):
            gate = self.gate()
            self.assertTrue(gate.admit(**self.request()))
            self.assertFalse(gate.admit(**self.request()))
            self.assertNotIn("private-canary", repr(gate.__dict__))
            self.assertEqual(len(self.contract.fingerprint()), 64)

    def test_target_aliases_queries_credentials_and_cross_fixture_endpoints_are_rejected(self):
        for endpoint in (self.contract.endpoint_url+"?password=x", self.contract.endpoint_url+"#x",
                         self.contract.endpoint_url.replace("127.0.0.1", "localhost"),
                         self.contract.endpoint_url.replace(":8000", ":8001"),
                         self.contract.endpoint_url.replace("http://", "http://user:pass@"),
                         ORIGIN+"/interactive-submit/login-rejected"):
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                replace(self.contract, endpoint_url=endpoint)

    def test_operation_fields_document_and_configuration_must_match(self):
        for changes in ({"fixture_id":"search-transition"}, {"fixture_id":"canary"},
                        {"document_url":ORIGIN+"/"}, {"field_names":["user","password"]},
                        {"field_names":("password","user")}, {"form":"plaintext"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError): replace(self.contract, **changes)
        for project, fingerprint in ((replace(self.project, allow_data_changes=False), "b"*64),
                                     (replace(self.project, project_id="c"*32), "b"*64),
                                     (replace(self.project, base_url=ORIGIN+"/"), "b"*64),
                                     (self.project, "d"*64)):
            with self.assertRaises(ValueError):
                OwnedSubmissionGate(self.contract, project, current_fingerprint=fingerprint)

    def test_malformed_or_extra_values_consume_the_only_attempt(self):
        bodies = (b"user=u&password=p&extra=x", b"user=u&password=p&password=q",
                  b"password=p&user=u", b"user=u", b"user=&password=p", b"user=u&password=%0D%0A",
                  b"user=u&password=%FF", b"user=u&password=%ZZ", b"user=u&password=%",
                  b"user=u&password="+b"x"*513, b"x"*8193, b"user=u&password=\xff", "user=u&password=p")
        for body in bodies:
            with self.subTest(body_type=type(body).__name__):
                gate=self.gate(); request=self.request(); request["body"]=body
                self.assertFalse(gate.admit(**request))
                self.assertFalse(gate.admit(**self.request()))

    def test_request_method_type_and_endpoint_cannot_expand_authority(self):
        for key,value in (("method","GET"), ("method","post"), ("content_type","application/json"),
                          ("url",self.contract.endpoint_url+"?x=1")):
            gate=self.gate(); request=self.request(); request[key]=value
            self.assertFalse(gate.admit(**request))
            self.assertFalse(gate.admit(**self.request()))

    def test_unicode_and_search_keep_explicit_distinct_bindings(self):
        request=self.request(); request["body"]=urlencode({"user":"deneme kullanıcı", "password":"a+b&=ş"}).encode("ascii")
        self.assertTrue(self.gate().admit(**request))
        form=InteractiveFormContract("a"*32,"b"*64,FormOperation.SEARCH,(SecretReference("FIXTURE_QUERY"),),
            ElementMapping("search.empty",(LocatorSpec(LocatorStrategy.TEST_ID,"negative"),)))
        contract=OwnedSubmissionContract(form,"search-empty",ORIGIN+"/interactive/search-empty",
            ORIGIN+"/interactive-submit/search-empty",("query",))
        project=replace(self.project,base_url=contract.document_url)
        gate=OwnedSubmissionGate(contract,project,current_fingerprint="b"*64)
        self.assertTrue(gate.admit(url=contract.endpoint_url,method="POST",content_type=CONTENT_TYPE,body=b"query=not-found"))
        self.assertNotEqual(contract.fingerprint(),self.contract.fingerprint())
