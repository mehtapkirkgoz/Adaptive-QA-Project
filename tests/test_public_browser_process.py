"""Reviewed browser IPC and lifecycle checks that do not require a browser install."""
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import monotonic
import unittest
from unittest.mock import patch

from tests import test_public_submission_process as fixtures
from adaptive_qa.element_models import ProjectElementMappings
from adaptive_qa.models import TestStatus
from adaptive_qa.public_browser_process import _encode, _decode, _read_result, run_isolated_public_browser
from adaptive_qa.secrets import SecretReference


class PublicBrowserProcessTests(unittest.TestCase):
    def setUp(self):fixtures.PublicSubmissionProcessTests.setUp(self)

    def run_child(self, **kwargs):
        return run_isolated_public_browser(self.review,self.project,owner_id=self.owner_id,
            current_fingerprint='b'*64,**kwargs)

    def test_reference_only_codec_and_foreign_mappings_fail_offline(self):
        with patch.object(SecretReference,'resolve',side_effect=AssertionError('No values')), \
                patch('socket.getaddrinfo',side_effect=AssertionError('No DNS')):
            raw=_encode(self.review,self.project,self.owner_id,'b'*64,None)
            self.assertEqual(_decode(raw),(self.review,self.project,self.owner_id,'b'*64,None))
            data=json.loads(raw)
            with self.assertRaises(ValueError):_decode(json.dumps({**data,'ignore_https_errors':True}))
            with self.assertRaises(ValueError):_encode(self.review,self.project,self.owner_id,'b'*64,ProjectElementMappings('d'*32))

    def test_precancel_invalid_bounds_and_callback_never_spawn(self):
        with patch('adaptive_qa.public_submission_process.subprocess.Popen') as spawn:
            self.assertEqual(self.run_child(should_cancel=lambda:True).status,TestStatus.CANCELLED)
            for timeout in (True,0,46,float('nan')):
                with self.assertRaises(ValueError):self.run_child(timeout_seconds=timeout)
            spawn.assert_not_called()

    def sleeping_child(self,mode):
        original=subprocess.Popen;children=[];started=monotonic()
        def spawn(command,**options):
            if 'adaptive_qa.public_browser_process' not in command:return original(command,**options)
            self.assertNotIn('SSLKEYLOGFILE',options['env'])
            self.assertNotIn(self.reference,' '.join(command))
            child=original([sys.executable,'-c','import time;time.sleep(60)'],**options)
            children.append(child);return child
        def cancel():
            if not children:return False
            if mode=='broken':raise RuntimeError('PRIVATE_EXCEPTION_CANARY')
            return mode=='cancel' and monotonic()-started>.1
        try:
            with patch('adaptive_qa.public_submission_process.subprocess.Popen',side_effect=spawn):
                result=self.run_child(timeout_seconds=.35,should_cancel=cancel)
            self.assertEqual(result.status,TestStatus.CANCELLED if mode=='cancel' else TestStatus.ERROR)
            self.assertIsNone(result.attempted_submissions)
            self.assertNotIn('PRIVATE_EXCEPTION_CANARY',repr(result))
        finally:
            for child in children:
                alive=child.poll() is None
                if alive:child.kill();child.wait(timeout=5)
                self.assertFalse(alive,'Owned browser child survived supervision')

    def test_hard_deadline_kills_owned_child(self):self.sleeping_child('deadline')
    def test_cancellation_kills_owned_child(self):self.sleeping_child('cancel')
    def test_failed_callback_kills_owned_child(self):self.sleeping_child('broken')

    def test_only_fixed_messages_and_real_submission_counts_are_accepted(self):
        with TemporaryDirectory() as directory:
            result=Path(directory).resolve()/'result.json'
            valid=dict(status='passed',message='The reviewed HTTP response and UI transition were verified.',attempted_submissions=1)
            result.write_text(json.dumps(valid),encoding='utf-8')
            self.assertEqual(_read_result(result).status,TestStatus.PASSED)
            for change in ({'attempted_submissions':0},{'attempted_submissions':True},
                           {'message':'PRIVATE_VALUE_CANARY'},{'raw_response':'echo'},
                           {'status':'cancelled'}):
                result.write_text(json.dumps({**valid,**change}),encoding='utf-8')
                with self.assertRaises(ValueError):_read_result(result)
