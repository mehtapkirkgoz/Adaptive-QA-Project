"""A changed release is refused before any wheel installation starts."""

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.check_release import check_release


class ReleaseVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.payload = self.directory / 'adaptive_qa-fixture.whl'
        self.payload.write_bytes(b'original release fixture')
        self.manifest = {'source_commit': 'a' * 40, 'activation_enabled': False,
                         'files': [{'name': self.payload.name, 'bytes': self.payload.stat().st_size,
                                    'sha256': hashlib.sha256(self.payload.read_bytes()).hexdigest()}]}
        self.write_manifest()

    def write_manifest(self):
        (self.directory / 'release.json').write_text(json.dumps(self.manifest), encoding='utf-8')

    def reject(self, expected):
        with patch('scripts.check_release.subprocess.check_output', return_value='a' * 40), \
                patch('scripts.check_release.subprocess.run', side_effect=AssertionError('No installation')):
            with self.assertRaisesRegex(ValueError, expected):
                check_release(self.directory)

    def test_modified_payload_is_rejected_before_installation(self):
        self.payload.write_bytes(b'modified release fixture')
        self.reject('digest or size')

    def test_mismatched_commit_is_rejected_before_installation(self):
        self.manifest['source_commit'] = 'b' * 40
        self.write_manifest()
        self.reject('checked-out commit')

    def test_unlisted_files_are_rejected_before_installation(self):
        (self.directory / 'unexpected.sqlite').write_bytes(b'private fixture')
        self.reject('file set')
