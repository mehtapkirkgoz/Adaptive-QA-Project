"""Count-only review on contrasting owned SQLite fixtures; no customer data."""
import hashlib
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from unittest.mock import patch
from adaptive_qa.config import ProjectConfig
from adaptive_qa.database_models import DatabaseConfiguration
from adaptive_qa.local_database_review import review_local_database,run_reviewed_local_database
from adaptive_qa.models import TestStatus
from adaptive_qa.secrets import SecretReference


def main():
    results=[]
    with TemporaryDirectory(prefix='owned-db-review-') as temporary:
        base=Path(temporary).resolve();fixtures=[]
        for name,table,count in (('catalog','inventory',3),('empty','stock_entries',0)):
            root=base/name;root.mkdir();path=root/'fixture.sqlite'
            with closing(sqlite3.connect(path)) as c,c:
                c.execute(f'CREATE TABLE "{table}" (label TEXT)')
                c.executemany(f'INSERT INTO "{table}" VALUES (?)',[('owned-value-canary',)]*count)
            fixtures.append((root,path,table,count,hashlib.sha256(path.read_bytes()).hexdigest()))
        config=DatabaseConfiguration(ProjectConfig('a'*32,'Owned SQLite','http://127.0.0.1:8000',('127.0.0.1',)),SecretReference('ADAPTIVE_OWNED_DB_PROOF'))
        for root,path,table,count,_ in fixtures:
            # A missing environment value cannot stop the non-executing review.
            with patch.dict(os.environ,{},clear=True):
                review=review_local_database(config,table=table,expected_count=count,fixture_root=root)
            with patch.dict(os.environ,{'ADAPTIVE_OWNED_DB_PROOF':str(path)}):
                result=run_reviewed_local_database(review,config,confirmed_fingerprint=review.fingerprint)
            assert result.status==TestStatus.PASSED and not result.evidence_paths
            assert 'owned-value-canary' not in result.message and str(path) not in result.message
            results.append(result.status.value)
        root,path,table,count,_=fixtures[0]
        mismatch=review_local_database(config,table=table,expected_count=count+1,fixture_root=root)
        with patch.dict(os.environ,{'ADAPTIVE_OWNED_DB_PROOF':str(path)}):
            result=run_reviewed_local_database(mismatch,config,confirmed_fingerprint=mismatch.fingerprint)
        assert result.status==TestStatus.FAILED;results.append(result.status.value)
        # A value resolving to a different owned directory is outside this review.
        with patch.dict(os.environ,{'ADAPTIVE_OWNED_DB_PROOF':str(fixtures[1][1])}):
            blocked=run_reviewed_local_database(mismatch,config,confirmed_fingerprint=mismatch.fingerprint)
        assert blocked.status==TestStatus.BLOCKED
        cancelled=run_reviewed_local_database(mismatch,config,confirmed_fingerprint=mismatch.fingerprint,should_cancel=lambda:True)
        assert cancelled.status==TestStatus.CANCELLED
        assert all(hashlib.sha256(path.read_bytes()).hexdigest()==digest for _,path,_,_,digest in fixtures)
    report=dict(owned_fixture_roots_only=True,configured_counts=results,outside_root='blocked',
        pre_cancelled=True,fixture_bytes_unchanged=True,resolved_paths_persisted=False,
        raw_rows_persisted=False,arbitrary_sql_accepted=False,catalog_expanded=False)
    output=Path('artifacts/database');output.mkdir(parents=True,exist_ok=True)
    (output/'reusable-review.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))


if __name__=='__main__':main()
