"""Inactive publication tolerates bounded Windows denial without overwriting."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.build_release import publish_bundle


class ReleasePublicationTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.bundle = self.base / '.build-owned' / 'bundle'
        self.bundle.mkdir(parents=True)
        (self.bundle / 'payload').write_bytes(b'inactive verified bytes')
        self.destination = self.base / ('a' * 40)

    @staticmethod
    def denied(code=5):
        error = PermissionError('Owned publication denied')
        error.winerror = code
        return error

    def test_real_publication_preserves_bytes_and_refuses_existing_destination(self):
        publish_bundle(self.bundle, self.destination, self.base)
        self.assertFalse(self.bundle.exists())
        self.assertEqual((self.destination / 'payload').read_bytes(), b'inactive verified bytes')
        self.bundle.mkdir()
        with self.assertRaisesRegex(ValueError, 'overwrite'):
            publish_bundle(self.bundle, self.destination, self.base)
        self.assertEqual((self.destination / 'payload').read_bytes(), b'inactive verified bytes')

    def test_temporary_windows_denial_retries_the_same_inactive_bundle(self):
        rename = Path.rename
        attempts = []
        def interrupted(source, destination):
            attempts.append((source, destination))
            if len(attempts) == 1:
                raise self.denied(32)
            return rename(source, destination)
        with patch('scripts.build_release.sys.platform', 'win32'), \
                patch.object(Path, 'rename', interrupted), \
                patch('scripts.build_release.time.sleep') as wait:
            publish_bundle(self.bundle, self.destination, self.base)
        self.assertEqual(attempts, [(self.bundle, self.destination)] * 2)
        wait.assert_called_once_with(.1)
        self.assertEqual((self.destination / 'payload').read_bytes(), b'inactive verified bytes')

    def test_permanent_denial_stops_without_publishing_or_losing_source(self):
        with patch('scripts.build_release.sys.platform', 'win32'), \
                patch.object(Path, 'rename', side_effect=self.denied()) as rename, \
                patch('scripts.build_release.time.sleep') as wait:
            with self.assertRaises(PermissionError):
                publish_bundle(self.bundle, self.destination, self.base)
        self.assertEqual(rename.call_count, 5)
        self.assertEqual(wait.call_count, 4)
        self.assertAlmostEqual(sum(call.args[0] for call in wait.call_args_list), 1.5)
        self.assertFalse(self.destination.exists())
        self.assertEqual((self.bundle / 'payload').read_bytes(), b'inactive verified bytes')

    def test_destination_created_during_wait_is_never_overwritten(self):
        def another_publisher(_):
            self.destination.mkdir()
            (self.destination / 'payload').write_bytes(b'other published bytes')
        with patch('scripts.build_release.sys.platform', 'win32'), \
                patch.object(Path, 'rename', side_effect=self.denied()) as rename, \
                patch('scripts.build_release.time.sleep', side_effect=another_publisher):
            with self.assertRaisesRegex(ValueError, 'overwrite'):
                publish_bundle(self.bundle, self.destination, self.base)
        self.assertEqual(rename.call_count, 1)
        self.assertEqual((self.destination / 'payload').read_bytes(), b'other published bytes')
        self.assertTrue(self.bundle.is_dir())

    def test_unrelated_errors_are_not_retried(self):
        for platform, error in [('linux', self.denied()), ('win32', self.denied(87))]:
            with self.subTest(platform=platform, code=error.winerror), \
                    patch('scripts.build_release.sys.platform', platform), \
                    patch.object(Path, 'rename', side_effect=error) as rename, \
                    patch('scripts.build_release.time.sleep') as wait:
                with self.assertRaises(PermissionError):
                    publish_bundle(self.bundle, self.destination, self.base)
                rename.assert_called_once()
                wait.assert_not_called()

    def test_outside_destination_is_rejected_before_rename(self):
        with patch.object(Path, 'rename') as rename:
            with self.assertRaisesRegex(ValueError, 'unsafe'):
                publish_bundle(self.bundle, self.base.parent / 'outside-release', self.base)
            rename.assert_not_called()


if __name__ == '__main__':
    unittest.main()
