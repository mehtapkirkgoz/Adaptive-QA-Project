"""Bounded screenshot import and atomic ownership-aware evidence storage."""

from pathlib import Path
import os
from tempfile import TemporaryDirectory
import unittest

import test_dashboard_runs as run_fixtures
from adaptive_qa.dashboard_evidence import import_screenshot, validate_png, MAX_PNG_BYTES
from adaptive_qa.dashboard_runs import TestRunNotFound
from adaptive_qa.models import TestResult, TestStatus
from png_fixture import png_bytes


class ScreenshotImportTests(unittest.TestCase):
    def test_valid_png_and_invalid_checksum_truncation_payload_and_dimensions(self):
        image = png_bytes()
        self.assertEqual(validate_png(image), image)
        for invalid in (image[:-3], image + b'<script>private</script>', b'<svg/>',
                        image[:-1] + bytes([image[-1] ^ 1]), png_bytes(20001, 1), b'x' * (MAX_PNG_BYTES + 1)):
            with self.assertRaises(ValueError):
                validate_png(invalid)

    def test_only_registered_uuid_png_inside_screenshot_directory_is_imported(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / 'screenshots'
            root.mkdir()
            valid = root / ('a' * 32 + '.png')
            valid.write_bytes(png_bytes())
            self.assertEqual(import_screenshot((str(valid),), root=root), png_bytes())
            outside = Path(directory) / ('b' * 32 + '.png')
            outside.write_bytes(png_bytes())
            for paths in ((str(outside),), (str(root / '..' / 'screenshots' / valid.name),),
                          (str(root / 'private.txt'),), (), (str(valid), str(valid))):
                self.assertIsNone(import_screenshot(paths, root=root))
            nonregular = root / ('c' * 32 + '.png')
            nonregular.mkdir()
            self.assertIsNone(import_screenshot((str(nonregular),), root=root))
            if hasattr(os, 'mkfifo'):
                fifo = root / ('d' * 32 + '.png')
                os.mkfifo(fifo)
                self.assertIsNone(import_screenshot((str(fifo),), root=root))

    def test_missing_or_invalid_optional_evidence_is_omitted(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / ('a' * 32 + '.png')
            self.assertIsNone(import_screenshot((str(path),), root=root))
            path.write_bytes(b'private raw text')
            self.assertIsNone(import_screenshot((str(path),), root=root))


class RunEvidenceTests(unittest.TestCase):
    def setUp(self):
        fixture = run_fixtures.DashboardRunsTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.queue = fixture.runs
        self.run = fixture.submit()
        self.work = self.queue.claim_next()

    def test_png_is_bound_to_owner_project_run_and_result_without_paths(self):
        self.queue.record_result(self.work, TestResult('LOGIN-001', TestStatus.PASSED, .1, 'raw path'), evidence_png=png_bytes())
        self.queue.finish(self.work)
        current = self.queue.get(self.fixture.actor, self.fixture.pid, self.run['run_id'])
        eid = current['results'][0]['evidence_id']
        self.assertEqual(self.queue.evidence(self.fixture.actor, self.fixture.pid, self.run['run_id'], eid), png_bytes())
        self.assertNotIn('raw path', str(current))
        with self.assertRaises(TestRunNotFound):
            self.queue.evidence(self.fixture.other, self.fixture.pid, self.run['run_id'], eid)
        second = self.fixture.submit()
        with self.assertRaises(TestRunNotFound):
            self.queue.evidence(self.fixture.actor, self.fixture.pid, second['run_id'], eid)

    def test_cancelled_late_result_stores_no_png_or_result(self):
        self.queue.cancel(self.fixture.actor, self.fixture.pid, self.run['run_id'])
        self.assertFalse(self.queue.record_result(self.work, TestResult('LOGIN-001', TestStatus.PASSED, .1, 'Late'), evidence_png=png_bytes()))
        self.queue.finish(self.work)
        with self.fixture.projects._connection() as connection:
            self.assertEqual(connection.execute('SELECT count(*) FROM dashboard_run_evidence').fetchone()[0], 0)

    def test_invalid_png_rejects_atomic_result_write(self):
        with self.assertRaises(ValueError):
            self.queue.record_result(self.work, TestResult('LOGIN-001', TestStatus.PASSED, .1, 'x'), evidence_png=b'private')
        self.assertEqual(self.queue.get(self.fixture.actor, self.fixture.pid, self.run['run_id'])['results'], [])
