"""Count-only review on contrasting owned SQLite fixtures; no customer data."""
import hashlib
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import shutil
from tempfile import TemporaryDirectory
from unittest.mock import patch
from adaptive_qa.config import ProjectConfig
from adaptive_qa.database_models import DatabaseConfiguration
from adaptive_qa.local_database_review import review_local_database,run_reviewed_local_database
from adaptive_qa.models import TestStatus
from adaptive_qa.secrets import SecretReference
from adaptive_qa.local_free import LocalFreeProjects,LOCAL_ACTOR
from adaptive_qa.project_settings import reference_name
from adaptive_qa.saved_database_review import review_saved_database
from adaptive_qa.database_queue import LocalDatabaseQueue,process_local_database_once


def main():
    results=[];saved_results=[]
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
        projects=LocalFreeProjects(base/'workspace'/'projects.sqlite')
        pid=projects.create(LOCAL_ACTOR,'Owned saved database').project_id
        owned_root=projects.database.parent/'database-fixtures'/pid;owned_root.mkdir(parents=True)
        owned_path=owned_root/'fixture.sqlite';shutil.copyfile(fixtures[0][1],owned_path)
        owned_digest=hashlib.sha256(owned_path.read_bytes()).hexdigest()
        variable=reference_name(LOCAL_ACTOR.user_id,pid,'database_path')
        queue=LocalDatabaseQueue(projects)
        for expected,private_path,status in ((3,owned_path,'passed'),(4,owned_path,'failed'),(3,fixtures[0][1],'blocked')):
            projects.save_configuration(LOCAL_ACTOR,pid,dict(base_url='http://127.0.0.1:8000',
                allowed_hosts=['127.0.0.1'],allow_data_changes=False,secret_references={'database_path':variable},
                local_database_binding=dict(table='inventory',expected_count=expected)))
            public=review_saved_database(projects,LOCAL_ACTOR,pid)
            job=queue.submit(LOCAL_ACTOR,pid,public['contract_fingerprint'])
            with patch.dict(os.environ,{variable:str(private_path)}):
                assert process_local_database_once(queue)['status']=='completed'
            assert queue.get(LOCAL_ACTOR,pid,job['job_id'])['result']==dict(status=status)
            assert process_local_database_once(queue) is None
            saved_results.append(status)
        assert hashlib.sha256(owned_path.read_bytes()).hexdigest()==owned_digest
        assert all(hashlib.sha256(path.read_bytes()).hexdigest()==digest for _,path,_,_,digest in fixtures)
    report=dict(owned_fixture_roots_only=True,configured_counts=results,outside_root='blocked',
        pre_cancelled=True,fixture_bytes_unchanged=True,resolved_paths_persisted=False,
        raw_rows_persisted=False,arbitrary_sql_accepted=False,catalog_expanded=False,
        saved_queue_results=saved_results,workspace_project_root_pinned=True)
    output=Path('artifacts/database');output.mkdir(parents=True,exist_ok=True)
    (output/'reusable-review.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))


if __name__=='__main__':main()
