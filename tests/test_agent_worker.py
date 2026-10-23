"""The outbound worker independently rejects commands, targets and policy widening."""

import unittest
from unittest.mock import patch
from adaptive_qa.agent_worker import run_once


class AgentWorkerTests(unittest.TestCase):
    def test_untrusted_work_cannot_start_browser_or_expand_targets(self):
        work = {'lease_id':'a'*32,'run_id':'b'*32,'case_ids':['LOGIN-001'],
                'configuration':{'base_url':'http://127.0.0.1:8000/','allowed_hosts':['127.0.0.1'],
                                 'allow_data_changes':False},'lease_seconds':120}
        variants = [dict(work,case_ids=['API-001']),dict(work,command='shell text'),
                    dict(work,lease_seconds=True),dict(work,case_ids=['LOGIN-001','LOGIN-001']),
                    dict(work,configuration=dict(work['configuration'],base_url='https://example.test/')),
                    dict(work,configuration=dict(work['configuration'],allow_data_changes=0))]
        class Client:
            def call(self,path,data): return {'work':self.work}
        client = Client()
        with patch('adaptive_qa.agent_worker.run_isolated_sample_test',side_effect=AssertionError('No execution')):
            for invalid in variants:
                client.work = invalid
                with self.assertRaises(ValueError):
                    run_once(client)
