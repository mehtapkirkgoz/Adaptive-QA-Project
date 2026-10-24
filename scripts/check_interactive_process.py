"""Actual child/browser transitions, hard deadlines and active cancellation on fixed DOM fixtures."""
import json
import os
from pathlib import Path
import subprocess
from time import monotonic
from unittest.mock import patch

from adaptive_qa.config import ProjectConfig
from adaptive_qa.element_models import ElementMapping,LocatorSpec,LocatorStrategy
from adaptive_qa.interactive_contracts import InteractiveFormContract,FormOperation
from adaptive_qa.interactive_fixtures import FIXTURES
from adaptive_qa.interactive_process import run_isolated_interactive_probe
from adaptive_qa.secrets import SecretReference


def main():
    reports=[]
    with patch.dict(os.environ,{'PROBE_USER':'owned-user-canary-64','PROBE_PASSWORD':'owned-password-canary-64','PROBE_QUERY':'owned-query-canary-64'}):
        for fixture_id,expected in (('login-transition','passed'),('login-rejected','passed'),('search-transition','passed'),
                                   ('search-empty','passed'),('no-transition','failed'),('canary','error'),('busy','error'),('busy','cancelled')):
            operation=FIXTURES[fixture_id]
            negative=fixture_id in ('login-rejected','search-empty')
            logical = ('login.rejected' if negative else 'login.accepted') if operation==FormOperation.LOGIN else ('search.empty' if negative else 'search.results')
            inputs=(SecretReference('PROBE_USER'),SecretReference('PROBE_PASSWORD')) if operation==FormOperation.LOGIN else (SecretReference('PROBE_QUERY'),)
            contract=InteractiveFormContract('a'*32,'b'*64,operation,inputs,
                ElementMapping(logical,(LocatorSpec(LocatorStrategy.TEST_ID,'negative' if negative else 'result'),)),5)
            project=ProjectConfig('a'*32,'Owned DOM process','http://127.0.0.1:8000/interactive/'+fixture_id,('127.0.0.1',),True)
            started=monotonic();children=[];original=subprocess.Popen
            def spawn(command,**options):
                if 'adaptive_qa.interactive_process' not in command:return original(command,**options)
                assert project.base_url not in command and 'PROBE_PASSWORD' not in command
                payload=Path(command[command.index('--input')+1]).read_text(encoding='utf-8')
                assert 'owned-password-canary-64' not in payload and 'owned-user-canary-64' not in payload
                child=original(command,**options);children.append(child);return child
            try:
                with patch('adaptive_qa.interactive_process.subprocess.Popen',side_effect=spawn):
                    result=run_isolated_interactive_probe(contract,project,fixture_id=fixture_id,current_fingerprint='b'*64,
                        timeout_seconds=3 if fixture_id=='busy' else 15,
                        should_cancel=(lambda:monotonic()-started>1.5) if expected=='cancelled' else None)
                assert result.status.value==expected,(fixture_id,result)
                assert result.attempted_submissions is None if fixture_id=='busy' else result.attempted_submissions in (0,1)
                assert all(child.poll() is not None for child in children)
                assert 'owned-password-canary-64' not in repr(result) and 'owned-user-canary-64' not in repr(result)
                reports.append(dict(fixture=fixture_id,status=result.status.value,attempted_submissions=result.attempted_submissions,owned_child_exited=True))
            finally:
                for child in children:
                    if child.poll() is None:child.kill();child.wait(timeout=5)
    output=Path('artifacts/interactive-probe');output.mkdir(parents=True,exist_ok=True)
    report=dict(fixed_dom_fixtures_only=True,http_submissions_enabled=False,screenshots_captured=0,scenarios=reports)
    (output/'process.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'scenarios':len(reports),'owned_children_exited':True,'http_submissions_enabled':False}))


if __name__=='__main__':main()
