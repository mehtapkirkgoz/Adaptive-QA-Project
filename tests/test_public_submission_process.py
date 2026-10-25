"""Hard supervision and reference-only child transport without customer endpoints."""
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import monotonic
import unittest
from unittest.mock import patch

try:
    from tests import test_public_submission as tls_fixture
except ImportError:
    import test_public_submission as tls_fixture

from adaptive_qa.config import ProjectConfig
from adaptive_qa.element_models import ElementMapping, LocatorSpec, LocatorStrategy
from adaptive_qa.interactive_contracts import FormOperation, InteractiveFormContract
from adaptive_qa.local_form_binding import LocalBooleanResponse
from adaptive_qa.project_settings import reference_name
from adaptive_qa.public_form_proposal import PublicFormProposal
from adaptive_qa.public_submission import ReviewedPublicForm
from adaptive_qa.public_submission_process import _decode, _encode, _read_result, run_isolated_public_submission
from adaptive_qa.public_submission_process import _private_directory
from adaptive_qa.secrets import SecretReference


class PublicSubmissionProcessTests(unittest.TestCase):
    def setUp(self):
        self.owner_id='c'*32
        self.reference=reference_name(self.owner_id,'a'*32,'search_query')
        form=InteractiveFormContract('a'*32,'b'*64,FormOperation.SEARCH,(SecretReference(self.reference),),
            ElementMapping('search.results',(LocatorSpec(LocatorStrategy.TEST_ID,'results-ready'),)))
        self.proposal=PublicFormProposal(form,'https://qa.example.test/search','https://qa.example.test/search/execute',
            ('query',),LocalBooleanResponse(200,'found',True),LocalBooleanResponse(404,'found',False))
        self.review=ReviewedPublicForm(self.proposal,self.proposal.fingerprint())
        self.project=ProjectConfig('a'*32,'Owned child TLS proof',self.proposal.document_url,('qa.example.test',),True)

    def run_child(self, **kwargs):
        return run_isolated_public_submission(self.review,self.project,owner_id=self.owner_id,
            current_fingerprint='b'*64,**kwargs)

    def test_metadata_roundtrip_is_reference_only_and_offline(self):
        with patch.object(SecretReference,'resolve',side_effect=AssertionError('No inputs')), \
                patch('socket.getaddrinfo',side_effect=AssertionError('No DNS')), \
                patch.dict(os.environ,{self.reference:'PRIVATE_VALUE_CANARY'}):
            raw=_encode(self.review,self.project,self.owner_id,'b'*64)
            self.assertNotIn('PRIVATE_VALUE_CANARY',raw)
            self.assertEqual(_decode(raw),(self.review,self.project,self.owner_id,'b'*64))

    def test_transient_windows_cleanup_lock_is_retried_but_persistent_failure_is_reported(self):
        from tempfile import TemporaryDirectory as OriginalDirectory
        created=[]
        def directory(*args,**kwargs):
            owned=OriginalDirectory(*args,**kwargs);created.append(owned)
            cleanup=owned.cleanup
            locked=PermissionError('Owned test directory temporarily locked');locked.winerror=32
            calls=[]
            def attempt():
                calls.append(True)
                if len(calls)<3:raise locked
                cleanup()
            owned.cleanup=attempt
            return owned
        with patch('adaptive_qa.public_submission_process.TemporaryDirectory',side_effect=directory), \
                patch('adaptive_qa.public_submission_process.sleep') as sleep:
            with _private_directory() as root:self.assertTrue(root.exists())
            self.assertFalse(root.exists());self.assertEqual(sleep.call_count,2)
        owned=OriginalDirectory(prefix='adaptive-public-submit-')
        self.addCleanup(owned.cleanup)
        locked=PermissionError('Persistent owned test lock');locked.winerror=32
        with patch('adaptive_qa.public_submission_process.TemporaryDirectory',return_value=owned), \
                patch.object(owned,'cleanup',side_effect=locked) as cleanup, \
                patch('adaptive_qa.public_submission_process.sleep'):
            with self.assertRaises(PermissionError):
                with _private_directory():pass
            self.assertEqual(cleanup.call_count,12)

    def test_wrong_owner_refs_policy_deadline_and_callback_never_spawn(self):
        with patch('adaptive_qa.public_submission_process.subprocess.Popen') as spawn:
            for timeout in (True,0,46,float('nan')):
                with self.assertRaises(ValueError):self.run_child(timeout_seconds=timeout)
            with self.assertRaises(ValueError):self.run_child(should_cancel=42)
            with self.assertRaises(ValueError):
                run_isolated_public_submission(self.review,self.project,owner_id='d'*32,current_fingerprint='b'*64)
            with self.assertRaises(ValueError):
                run_isolated_public_submission(self.review,replace(self.project,allow_data_changes=False),
                    owner_id=self.owner_id,current_fingerprint='b'*64)
            spawn.assert_not_called()

    def test_precancel_and_failed_source_never_spawn(self):
        def broken():raise RuntimeError('PRIVATE_EXCEPTION_CANARY')
        with patch('adaptive_qa.public_submission_process.subprocess.Popen') as spawn:
            cancelled=self.run_child(should_cancel=lambda:True)
            self.assertEqual((cancelled.outcome,cancelled.attempted_submissions),('cancelled',0))
            failed=self.run_child(should_cancel=broken)
            self.assertEqual(failed.reason_code,'cancellation_source_failed')
            self.assertNotIn('PRIVATE_EXCEPTION_CANARY',repr(failed))
            spawn.assert_not_called()

    def owned_sleeping_child(self, mode):
        original=subprocess.Popen;children=[];started=monotonic()
        def spawn(command,**options):
            if 'adaptive_qa.public_submission_process' not in command:
                return original(command,**options)
            self.assertIn('adaptive_qa.public_submission_process',command)
            self.assertNotIn('SSLKEYLOGFILE',options['env'])
            self.assertNotIn(reference_name('d'*32,'e'*32,'login_password'),options['env'])
            self.assertEqual(options['env'][self.reference],'PRIVATE_VALUE_CANARY')
            self.assertNotIn(self.reference,' '.join(command))
            source=Path(command[command.index('--input')+1])
            self.assertNotIn('PRIVATE_VALUE_CANARY',source.read_text(encoding='utf-8'))
            child=original([sys.executable,'-c','import time;time.sleep(60)'],**options)
            children.append(child);return child
        def cancel():
            if not children:return False
            if mode=='broken':raise RuntimeError('PRIVATE_EXCEPTION_CANARY')
            return mode=='cancel' and monotonic()-started>.1
        try:
            with patch('adaptive_qa.public_submission_process.subprocess.Popen',side_effect=spawn), \
                    patch.dict(os.environ,{self.reference:'PRIVATE_VALUE_CANARY',
                        reference_name('d'*32,'e'*32,'login_password'):'OTHER_PROJECT_VALUE_CANARY'}):
                result=self.run_child(timeout_seconds=.35,should_cancel=cancel)
            self.assertEqual(result.reason_code,{'deadline':'deadline_exceeded','cancel':'cancelled',
                'broken':'cancellation_source_failed'}[mode])
            self.assertIsNone(result.attempted_submissions)
        finally:
            for child in children:
                alive=child.poll() is None
                if alive:child.kill();child.wait(timeout=5)
                self.assertFalse(alive,'Owned child survived supervision')

    def test_hard_deadline_kills_owned_process(self):self.owned_sleeping_child('deadline')
    def test_cancellation_kills_owned_process(self):self.owned_sleeping_child('cancel')
    def test_failed_cancellation_source_kills_owned_process(self):self.owned_sleeping_child('broken')

    def test_untrusted_metadata_and_result_values_fail_closed(self):
        raw=_encode(self.review,self.project,self.owner_id,'b'*64)
        data=json.loads(raw)
        for altered in ({**data,'password':'plaintext'}, {**data,'owner_id':'d'*32},
                        {**data,'confirmed_fingerprint':'e'*64}):
            with self.assertRaises(ValueError):_decode(json.dumps(altered))
        with self.assertRaises(ValueError):_decode('x'*16385)
        with TemporaryDirectory() as directory:
            result=Path(directory).resolve()/'result.json'
            for value in ({'outcome':'accepted','reason_code':'response_accepted','attempted_submissions':True},
                          {'outcome':'blocked','reason_code':'preconditions_blocked','attempted_submissions':1},
                          {'outcome':'error','reason_code':'PRIVATE_EXCEPTION_CANARY','attempted_submissions':None},
                          {'outcome':'accepted','reason_code':'response_accepted','attempted_submissions':1,'raw_body':'echo'}):
                result.write_text(json.dumps(value),encoding='utf-8')
                with self.assertRaises(ValueError):_read_result(result)

    def real_owned_tls_child(self, *, private=False, missing=False, drop=False, slow=False, timeout_seconds=10):
        _,_,state=tls_fixture.PublicSubmissionTests.tls_harness(self)
        state.update(drop=drop,slow=slow)
        original=subprocess.Popen
        # The wrapper is test-only. Production exposes no connector or CA override.
        wrapper=f'''import sys,socket,ssl
import adaptive_qa.egress as egress
from adaptive_qa.egress import DestinationGuard
from adaptive_qa.secrets import SecretReference
from adaptive_qa.public_submission_process import main
original_context=ssl.create_default_context
count=[0]
def resolve(host,port):
    count[0]+=1
    return {('127.0.0.1',) if private else ('93.184.216.34',)!r}
def connect(guard,target,**kwargs):
    assert not guard.local_sample and target.hostname=='qa.example.test' and target.port==443
    assert target.addresses==('93.184.216.34',)
    return socket.create_connection(('127.0.0.1',{state['port']}),timeout=2)
egress.resolve_with_deadline=resolve
DestinationGuard.connect=connect
ssl.create_default_context=lambda:original_context(cafile={state['ca_path']!r})
if {private!r}:
    def no_values(self):raise AssertionError('Private destination must not resolve input')
    SecretReference.resolve=no_values
sys.argv=['owned-proof']+sys.argv[1:]
main()
assert count[0]==1
'''
        def spawn(command,**options):
            if 'adaptive_qa.public_submission_process' not in command:
                return original(command,**options)
            self.assertIn('adaptive_qa.public_submission_process',command)
            self.assertNotIn('OWNED_CHILD_INPUT_CANARY',' '.join(command))
            return original([sys.executable,'-c',wrapper,*command[3:]],**options)
        with patch.dict(os.environ,{self.reference:'OWNED_CHILD_INPUT_CANARY'}):
            if missing:os.environ.pop(self.reference)
            with patch('adaptive_qa.public_submission_process.subprocess.Popen',side_effect=spawn):
                result=self.run_child(timeout_seconds=timeout_seconds)
        self.assertNotIn('OWNED_CHILD_INPUT_CANARY',repr(result))
        return result,state

    def test_real_child_keeps_values_private_and_checks_owned_tls_response(self):
        result,state=self.real_owned_tls_child()
        self.assertEqual((result.outcome,result.attempted_submissions),('accepted',1))
        self.assertEqual(len(state['contacts']),1)
        self.assertEqual(state['contacts'][0]['body'],b'query=OWNED_CHILD_INPUT_CANARY')

    def test_real_child_private_dns_and_missing_reference_send_no_post(self):
        for change in ({'private':True},{'missing':True}):
            result,state=self.real_owned_tls_child(**change)
            self.assertEqual((result.outcome,result.attempted_submissions),('blocked',0))
            self.assertEqual(state['contacts'],[])

    def test_real_child_lost_response_stays_uncertain(self):
        result,state=self.real_owned_tls_child(drop=True)
        self.assertEqual(result.outcome,'error');self.assertIsNone(result.attempted_submissions)
        self.assertEqual(len(state['contacts']),1)

    def test_hard_deadline_stops_a_real_slow_tls_response_without_retry(self):
        result,state=self.real_owned_tls_child(slow=True,timeout_seconds=3)
        self.assertEqual(result.reason_code,'deadline_exceeded')
        self.assertIsNone(result.attempted_submissions)
        self.assertEqual(len(state['contacts']),1)
