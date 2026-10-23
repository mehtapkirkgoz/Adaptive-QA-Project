"""Publisher tooling generates only ephemeral test keys and never overwrites files."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time
import unittest
from unittest.mock import patch

from adaptive_qa.licensing import verify_license

spec = importlib.util.spec_from_file_location('offline_issuer',Path(__file__).resolve().parents[1]/'scripts/issue_local_license.py')
issuer = importlib.util.module_from_spec(spec); spec.loader.exec_module(issuer)


class LocalIssuerTests(unittest.TestCase):
    def test_ephemeral_key_and_license_roundtrip_without_network_or_secret_output(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            private,public,output = (root/name for name in ('issuer.key','public.json','customer.json'))
            common = ['--private-key',str(private),'--key-id','test-publisher']
            log = io.StringIO()
            with redirect_stdout(log), patch('socket.getaddrinfo',side_effect=AssertionError('No DNS')):
                issuer.main(['generate-key',*common,'--public-keys',str(public)])
                issuer.main(['issue',*common,'--output',str(output),'--customer-id','a'*32,'--license-id','b'*32,
                    '--expires-at',str(int(time.time())+3600),'--max-projects','5','--max-concurrent-runs','2'])
            keys = {key:bytes.fromhex(value) for key,value in json.loads(public.read_text()).items()}
            self.assertEqual(verify_license(output.read_bytes(),keys).max_projects,5)
            self.assertNotIn(private.read_bytes().hex(),log.getvalue())
            with self.assertRaises(ValueError): issuer.main(['generate-key',*common,'--public-keys',str(public)])
            previous = output.read_bytes()
            with self.assertRaises(FileExistsError):
                issuer.main(['issue',*common,'--output',str(output),'--customer-id','a'*32,'--license-id','b'*32,
                    '--expires-at',str(int(time.time())+3600)])
            self.assertEqual(output.read_bytes(),previous)

    def test_repository_paths_and_invalid_claims_are_refused(self):
        with self.assertRaises(ValueError): issuer.external_path(issuer.REPOSITORY/'private.key')
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            private,public,output = (root/name for name in ('issuer.key','public.json','customer.json'))
            common = ['--private-key',str(private),'--key-id','test']
            with redirect_stdout(io.StringIO()): issuer.main(['generate-key',*common,'--public-keys',str(public)])
            with self.assertRaises(ValueError):
                issuer.main(['issue',*common,'--output',str(output),'--customer-id','a'*32,'--license-id','b'*32,
                    '--expires-at','1'])
            self.assertFalse(output.exists())
