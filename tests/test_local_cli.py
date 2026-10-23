"""Customer commands select licensed stores and keep imports entirely local."""
import argparse
import base64
from contextlib import redirect_stdout
from dataclasses import asdict
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from adaptive_qa.local_cli import configure_parser, load_trusted_keys, run
from adaptive_qa.licensing import LicenseClaims, license_message
from adaptive_qa.local_licensed import LicensedLocalProjects


class LocalCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.keys = self.root/'issuer.json'
        self.private = Ed25519PrivateKey.generate()
        self.keys.write_text(json.dumps({'issuer':self.private.public_key().public_bytes_raw().hex()}), encoding='utf-8')
        now = int(time.time())
        payload = asdict(LicenseClaims('a'*32, 'b'*32, now-10, now-10, now+3600, 4, 2))
        signature = base64.urlsafe_b64encode(self.private.sign(license_message('issuer', payload))).rstrip(b'=').decode()
        self.document = self.root/'customer.json'
        self.document.write_text(json.dumps(dict(key_id='issuer',payload=payload,signature=signature)), encoding='utf-8')
        self.parser = argparse.ArgumentParser()
        configure_parser(self.parser.add_subparsers(dest='command'))

    def invoke(self, command, *extra):
        args = self.parser.parse_args(['local',command,'--workspace',str(self.root/'workspace'),
            '--trusted-keys',str(self.keys), *extra])
        out = io.StringIO()
        with redirect_stdout(out): run(args)
        return out.getvalue()

    def test_import_and_status_do_not_print_ids_or_contact_network(self):
        with patch('socket.getaddrinfo',side_effect=AssertionError('No DNS')):
            self.assertEqual(json.loads(self.invoke('license-status'))['status'], 'absent')
            self.invoke('license-import','--license-file',str(self.document))
            status = json.loads(self.invoke('license-status'))
        self.assertEqual(status['max_projects'], 4)
        self.assertEqual(status['max_concurrent_runs'], 2)
        self.assertNotIn('customer_id',status)
        self.document.write_bytes(b'{}')
        with self.assertRaises(ValueError): self.invoke('license-import','--license-file',str(self.document))
        self.assertEqual(json.loads(self.invoke('license-status'))['status'],'valid')

    def test_worker_commands_always_construct_licensed_projects(self):
        for command, module, function in (('discovery-once','adaptive_qa.dashboard_worker','process_discovery_once'),
                                          ('run-once','adaptive_qa.dashboard_run_worker','process_run_once')):
            with self.subTest(command=command), patch(module+'.'+function, return_value=None) as process:
                self.invoke(command)
                self.assertIsInstance(process.call_args.args[0].projects, LicensedLocalProjects)
        # Without a license, no queue item can actually be claimed.
        self.assertIn('No licensed work',self.invoke('discovery-once'))

    def test_trust_files_are_bounded_and_duplicate_keys_rejected(self):
        for data in (b'{}', b'[]', b'x'*4097, b'{"issuer":"one","issuer":"two"}', b'\xff'):
            self.keys.write_bytes(data)
            with self.assertRaisesRegex(ValueError,'Invalid trusted public-key configuration'):
                load_trusted_keys(self.keys)

    def test_local_serve_uses_existing_admin_and_loopback(self):
        from adaptive_qa.auth_store import AuthStore
        root = self.root/'workspace'
        auth = AuthStore(root/'auth.sqlite')
        auth.create_user('owner@example.test','long owner password')
        ui = self.root/'ui'; ui.mkdir(); (ui/'assets').mkdir(); (ui/'index.html').write_text('<html></html>',encoding='utf-8')
        with patch('uvicorn.run') as serve:
            self.invoke('serve','--administrator','owner@example.test','--ui-directory',str(ui))
        self.assertEqual(serve.call_args.kwargs['host'],'127.0.0.1')
        self.assertEqual(serve.call_args.kwargs['workers'],1)
        with self.assertRaises(ValueError): self.invoke('serve','--administrator','missing@example.test')

    def test_backup_and_restore_commands_do_not_require_trust_or_activate_runtime(self):
        from adaptive_qa.local_free import create_free_app
        workspace = self.root/'workspace'
        create_free_app(workspace/'projects.sqlite')
        snapshot,recovered = self.root/'snapshot',self.root/'recovered'
        for command,extra in (('backup',[]),('restore',['--snapshot',str(snapshot)])):
            destination = snapshot if command=='backup' else recovered
            args = self.parser.parse_args(['local',command,'--workspace',str(workspace),
                '--destination',str(destination),'--maintenance-confirmed',*extra])
            out = io.StringIO()
            with redirect_stdout(out): run(args)
            self.assertFalse(json.loads(out.getvalue())['activation_enabled'])
        self.assertTrue((recovered/'projects.sqlite').is_file())
