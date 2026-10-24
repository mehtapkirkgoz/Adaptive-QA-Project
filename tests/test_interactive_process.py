"""Hard process bounds and strict, sanitized, reference-only probe transport."""
from dataclasses import asdict,replace
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import monotonic
import unittest
from unittest.mock import patch

from adaptive_qa.config import ProjectConfig
from adaptive_qa.element_models import ElementMapping,LocatorSpec,LocatorStrategy
from adaptive_qa.interactive_contracts import InteractiveFormContract,FormOperation
from adaptive_qa.interactive_process import _decode,_read_result,MESSAGES,run_isolated_interactive_probe
from adaptive_qa.models import TestStatus
from adaptive_qa.secrets import SecretReference


class InteractiveProcessTests(unittest.TestCase):
    def setUp(self):
        self.project=ProjectConfig('a'*32,'Controlled','http://127.0.0.1:8000/interactive/login-transition',('127.0.0.1',),True)
        self.contract=InteractiveFormContract('a'*32,'b'*64,FormOperation.LOGIN,(SecretReference('PROBE_USER'),SecretReference('PROBE_PASSWORD')),
            ElementMapping('login.accepted',(LocatorSpec(LocatorStrategy.TEST_ID,'result'),)),5)

    def run_probe(self,**kwargs):
        return run_isolated_interactive_probe(self.contract,self.project,fixture_id='login-transition',current_fingerprint='b'*64,**kwargs)

    def test_invalid_target_permission_and_deadline_never_spawn_or_resolve_inputs(self):
        with patch('adaptive_qa.interactive_process.subprocess.Popen') as spawn,patch.object(SecretReference,'resolve',side_effect=AssertionError('No secret access')):
            for deadline in (True,0,61,float('nan'),float('inf'),10**1000):
                with self.assertRaises(ValueError):self.run_probe(timeout_seconds=deadline)
            for project in (replace(self.project,allow_data_changes=False),replace(self.project,base_url='http://127.0.0.1:8000/other')):
                with self.assertRaises(ValueError):run_isolated_interactive_probe(self.contract,project,fixture_id='login-transition',current_fingerprint='b'*64)
            with self.assertRaises(ValueError):self.run_probe(fixture_source='external')
            self.assertEqual(self.run_probe(should_cancel=lambda:True).status,TestStatus.CANCELLED)
            spawn.assert_not_called()

    def test_codec_revalidates_types_and_never_resolves_references(self):
        payload=dict(contract=asdict(self.contract),project=asdict(self.project),fixture_id='login-transition',current_fingerprint='b'*64,fixture_source='memory')
        with patch.object(SecretReference,'resolve',side_effect=AssertionError('No secret access')):
            self.assertEqual(_decode(json.dumps(payload))[0],self.contract)
        for raw in ('{}','{"contract":{},"contract":{}}',json.dumps({**payload,'unexpected':'value'}),
                    json.dumps({**payload,'contract':{**payload['contract'],'inputs':['plaintext','secret']}})):
            with self.assertRaises(ValueError):_decode(raw)

    def test_child_start_failure_returns_a_sanitized_unknown_count(self):
        with patch('adaptive_qa.interactive_process.subprocess.Popen',side_effect=OSError('private process detail')):
            result=self.run_probe()
        self.assertEqual(result.status,TestStatus.ERROR)
        self.assertIsNone(result.attempted_submissions)
        self.assertNotIn('private',repr(result))

    def test_child_result_cannot_echo_input_or_claim_pass_without_submission(self):
        with TemporaryDirectory() as temporary:
            path=Path(temporary)/'result.json'
            for data in (dict(status='passed',message='private-value',attempted_submissions=1),
                         dict(status='passed',message=MESSAGES[TestStatus.PASSED],attempted_submissions=0),
                         dict(status='passed',message=MESSAGES[TestStatus.PASSED],attempted_submissions=True)):
                path.write_text(json.dumps(data),encoding='utf-8')
                with self.assertRaises(ValueError):_read_result(path)
            path.write_bytes(b'x'*4097)
            with self.assertRaises(ValueError):_read_result(path)

    def owned_process(self,mode):
        original=subprocess.Popen;children=[];started=monotonic()
        def spawn(command,**options):
            if 'adaptive_qa.interactive_process' not in command:return original(command,**options)
            self.assertNotIn(self.project.base_url,command)
            self.assertNotIn('PROBE_PASSWORD',command)
            child=original([sys.executable,'-c','import time;time.sleep(60)'],**options)
            children.append(child);return child
        def cancel():
            if children and mode=='callback-error':raise RuntimeError('sensitive callback detail')
            return bool(children) and mode=='cancel' and monotonic()-started>.1
        try:
            with patch('adaptive_qa.interactive_process.subprocess.Popen',side_effect=spawn):
                result=self.run_probe(timeout_seconds=.4,should_cancel=cancel)
            self.assertEqual(result.status,TestStatus.CANCELLED if mode=='cancel' else TestStatus.ERROR)
            self.assertIsNone(result.attempted_submissions)
            self.assertNotIn('sensitive',repr(result))
            self.assertTrue(all(child.poll() is not None for child in children),'Owned child survived supervisor return')
        finally:
            for child in children:
                if child.poll() is None:child.kill();child.wait(timeout=5)

    def test_deadline_terminates_owned_child(self):self.owned_process('deadline')
    def test_active_cancellation_terminates_owned_child(self):self.owned_process('cancel')
    def test_callback_failure_terminates_owned_child(self):self.owned_process('callback-error')
