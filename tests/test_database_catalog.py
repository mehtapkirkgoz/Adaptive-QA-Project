"""Catalog identity and exclusive fixture ownership checks."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from adaptive_qa.database_catalog import DATABASE_CASES, DATABASE_BY_ID
from adaptive_qa.sample_database import prepare_sample_database


class DatabaseCatalogTests(unittest.TestCase):
    def test_database_definitions_have_unique_read_only_identities(self):
        self.assertEqual(len(DATABASE_BY_ID), 15)
        self.assertEqual(set(DATABASE_BY_ID), {f'DB-{n:03}' for n in range(1, 16)})
        self.assertTrue(all(not case.definition.changes_data for case in DATABASE_CASES))

    def test_preparation_never_overwrites_existing_user_file(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / 'existing.db'
            path.write_bytes(b'user-owned-content')
            with self.assertRaises(FileExistsError):
                prepare_sample_database(path)
            self.assertEqual(path.read_bytes(), b'user-owned-content')
