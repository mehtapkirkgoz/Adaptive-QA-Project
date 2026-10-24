"""Explicit DB review does not resolve paths or accept arbitrary SQL authority."""
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from adaptive_qa.config import ProjectConfig
from adaptive_qa.database_models import DatabaseConfiguration
from adaptive_qa.local_database_review import review_local_database,run_reviewed_local_database
from adaptive_qa.secrets import SecretReference


class LocalDatabaseReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'owned';self.root.mkdir()
        self.config=DatabaseConfiguration(ProjectConfig('a'*32,'Owned DB','http://127.0.0.1:8000',('127.0.0.1',)),SecretReference('OWNED_DB_PATH'))

    def review(self,**changes):
        return review_local_database(self.config,**dict(dict(table='records',expected_count=2,fixture_root=self.root),**changes))

    def test_review_opens_no_database_resolves_no_reference_and_hides_private_root(self):
        with patch('sqlite3.connect',side_effect=AssertionError('No SQLite')), \
             patch.object(SecretReference,'resolve',side_effect=AssertionError('No values')):
            review=self.review()
        self.assertNotIn(str(self.root),repr(review))
        self.assertNotEqual(review.fingerprint,self.review(expected_count=3).fingerprint)
        self.assertEqual(review.case.template.sql,'SELECT COUNT(*) FROM "records"')

    def test_arbitrary_sql_identifiers_counts_and_customer_origin_are_rejected(self):
        for table in ('records;DROP TABLE records','sqlite_master','records.name','Records','../records'):
            with self.assertRaises(ValueError):self.review(table=table)
        for count in (True,-1,2147483648,1.0):
            with self.assertRaises(ValueError):self.review(expected_count=count)
        other=replace(self.config,project=replace(self.config.project,base_url='https://example.test',allowed_hosts=('example.test',)))
        with self.assertRaises(ValueError):review_local_database(other,table='records',expected_count=2,fixture_root=self.root)

    def test_confirmation_current_configuration_and_directory_identity_are_required(self):
        review=self.review()
        with patch('adaptive_qa.database_process.run_isolated_database_case') as child:
            for config,digest in ((self.config,'0'*64),(replace(self.config,max_rows=1),review.fingerprint)):
                with self.assertRaises(ValueError):run_reviewed_local_database(review,config,confirmed_fingerprint=digest)
            self.root.rename(self.root.with_name('old'));self.root.mkdir()
            with self.assertRaises(ValueError):run_reviewed_local_database(review,self.config,confirmed_fingerprint=review.fingerprint)
        child.assert_not_called()

    def test_dispatch_retains_bounded_existing_child_and_cancellation(self):
        review=self.review();cancel=lambda:True
        with patch('adaptive_qa.database_process.run_isolated_database_case',return_value='cancelled') as child:
            self.assertEqual(run_reviewed_local_database(review,self.config,confirmed_fingerprint=review.fingerprint,should_cancel=cancel),'cancelled')
        self.assertEqual(child.call_args.kwargs,dict(timeout_seconds=15,fixture_root=self.root.resolve(),should_cancel=cancel))
