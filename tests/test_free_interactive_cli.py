"""Free worker commands cannot silently open licensed state or create accounts."""
import argparse
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from adaptive_qa.dashboard_cli import configure_parser,run
from adaptive_qa.local_free import LocalFreeProjects


class FreeInteractiveCliTests(unittest.TestCase):
    def test_free_cycle_uses_free_store_and_refuses_licensed_workspace(self):
        parser=argparse.ArgumentParser();configure_parser(parser.add_subparsers(dest='command'))
        args=parser.parse_args(['dashboard','free-worker-cycle'])
        self.assertEqual(args.database,Path('artifacts/local-free/projects.sqlite'))
        with TemporaryDirectory() as temporary:
            args.database=Path(temporary)/'projects.sqlite'
            output=io.StringIO()
            with redirect_stdout(output), patch('socket.getaddrinfo',side_effect=AssertionError('No DNS')):
                run(args)
            self.assertEqual(json.loads(output.getvalue()),dict(discovery=None,run=None,interactive=None))
            self.assertFalse(args.database.with_name('auth.sqlite').exists())
            args.database.with_name('license.sqlite').write_bytes(b'owned marker')
            with patch('adaptive_qa.local_worker_cycle.process_local_cycle') as worker,self.assertRaises(ValueError):
                run(args)
            worker.assert_not_called()

    def test_free_worker_defaults_and_license_marker_guard(self):
        parser=argparse.ArgumentParser();configure_parser(parser.add_subparsers(dest='command'))
        args=parser.parse_args(['dashboard','free-interactive-once'])
        self.assertEqual(args.database,Path('artifacts/local-free/projects.sqlite'))
        with TemporaryDirectory() as temporary:
            args.database=Path(temporary)/'projects.sqlite'
            with patch('adaptive_qa.interactive_queue.process_owned_interactive_once',return_value=None) as worker,redirect_stdout(io.StringIO()):run(args)
            self.assertIsInstance(worker.call_args.args[0].projects,LocalFreeProjects)
            self.assertFalse(args.database.with_name('auth.sqlite').exists())
            args.database.with_name('license.sqlite').write_bytes(b'owned marker')
            with patch('adaptive_qa.interactive_queue.process_owned_interactive_once') as worker,self.assertRaises(ValueError):run(args)
            worker.assert_not_called()
