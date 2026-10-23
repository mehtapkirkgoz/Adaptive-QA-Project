"""Signed HTTP bodies, browser isolation, size and target boundaries."""

import base64
import json
import unittest
from fastapi.testclient import TestClient
import test_agent_broker as broker_fixtures
from adaptive_qa.agent_transport import create_agent_coordinator,validate_coordinator,MAX_MESSAGE
from adaptive_qa.agent_registry import message_signature,token_signing_key
from png_fixture import png_bytes


class AgentTransportTests(unittest.TestCase):
    def setUp(self):
        self.f = broker_fixtures.AgentBrokerTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.client = TestClient(create_agent_coordinator(self.f.broker,port=8871),base_url='http://127.0.0.1:8871')
        self.addCleanup(self.client.close)
        self.key = token_signing_key(self.f.grant.token.value)
        self.sequence = 1 # The broker fixture consumed sequence one during setup.

    def signed(self,path,data):
        self.sequence+=1
        raw = json.dumps(data,separators=(',',':')).encode()
        headers = {'content-type':'application/json','x-agent-id':self.f.grant.agent_id,
                   'x-agent-sequence':str(self.sequence),
                   'x-agent-signature':message_signature(self.key,path,self.sequence,raw)}
        return raw,headers

    def call(self,path,data):
        raw,headers = self.signed(path,data)
        response = self.client.post(path,content=raw,headers=headers)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.headers['x-agent-response-signature'],
                         message_signature(self.key,path,self.sequence,response.content,response=True))
        return response.json()

    def test_authenticated_poll_result_png_and_finish_have_signed_responses(self):
        self.f.f.submit()
        lease = self.call('/agent/poll',{})['work']
        self.assertNotIn('claim_token',lease)
        self.assertFalse(self.call('/agent/check',{'lease_id':lease['lease_id']})['cancel_requested'])
        result = self.call('/agent/result',{'lease_id':lease['lease_id'],'case_id':'LOGIN-001',
            'status':'passed','duration_seconds':.1,'png_base64':base64.b64encode(png_bytes()).decode()})
        self.assertTrue(result['accepted'])
        self.assertEqual(self.call('/agent/finish',{'lease_id':lease['lease_id'],'failed':False})['status'],'completed')

    def test_replayed_or_modified_signed_message_is_rejected_without_second_claim(self):
        self.f.f.submit()
        raw,headers = self.signed('/agent/poll',{})
        self.assertEqual(self.client.post('/agent/poll',content=raw,headers=headers).status_code,200)
        self.assertEqual(self.client.post('/agent/poll',content=raw,headers=headers).status_code,401)
        raw,headers = self.signed('/agent/check',{'lease_id':'a'*32})
        self.assertEqual(self.client.post('/agent/check',content=b'{}',headers=headers).status_code,401)

    def test_browser_proxy_duplicate_headers_and_wrong_origin_are_rejected(self):
        for extra in ({'origin':'http://127.0.0.1:8871'},{'cookie':'adaptive_session=ignored'},
                      {'host':'untrusted.test:8871'},{'x-forwarded-host':'127.0.0.1:8871'},
                      {'authorization':'Bearer ignored'}):
            raw,headers = self.signed('/agent/poll',{})
            self.assertEqual(self.client.post('/agent/poll',content=raw,headers={**headers,**extra}).status_code,400)
        raw,headers = self.signed('/agent/poll',{})
        duplicate = list(headers.items())+[('x-agent-id',self.f.grant.agent_id)]
        self.assertEqual(self.client.post('/agent/poll',content=raw,headers=duplicate).status_code,400)
        self.assertEqual(self.client.get('/agent/poll').status_code,404)

    def test_oversized_or_injected_fields_do_not_dispatch(self):
        raw,headers = self.signed('/agent/poll',{})
        self.assertEqual(self.client.post('/agent/poll',content=b'x'*(MAX_MESSAGE+1),headers=headers).status_code,413)
        raw,headers = self.signed('/agent/poll',{'url':'https://untrusted.test'})
        self.assertEqual(self.client.post('/agent/poll',content=raw,headers=headers).status_code,400)
        with self.f.f.projects._connection() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM dashboard_agent_leases').fetchone()[0],0)

    def test_only_exact_numeric_loopback_coordinator_origin_is_supported(self):
        self.assertEqual(validate_coordinator('http://127.0.0.1:8871'),8871)
        for origin in ('https://example.test','http://localhost:8871','http://127.0.0.1:8871/',
                       'http://127.0.0.1:8871?token=private','http://127.0.0.1:80',
                       'http://127.0.0.1:8871@untrusted.test','http://127.0.0.1:08871'):
            with self.assertRaises(ValueError):
                validate_coordinator(origin)
