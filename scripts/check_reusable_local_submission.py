"""Contrasting owned endpoint/field/response bindings without fixed fixture IDs."""
from http.server import BaseHTTPRequestHandler
from pathlib import Path
import json
import socket
from urllib.parse import urlencode
from check_owned_submission import server
from adaptive_qa.config import ProjectConfig
from adaptive_qa.element_models import ElementMapping,LocatorSpec,LocatorStrategy
from adaptive_qa.interactive_contracts import FormOperation,InteractiveFormContract
from adaptive_qa.local_form_binding import LocalFormBinding,LocalBooleanResponse
from adaptive_qa.owned_submission import OwnedSubmissionTransport,CONTENT_TYPE
from adaptive_qa.secrets import SecretReference


def main():
    state=dict(mode='accepted',posts=0,canary=0,bad=0,path='',body=b'',status=201,field='authenticated')
    class Canary(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):state['canary']+=1;self.send_error(403)
    class Endpoint(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            state['posts']+=1
            body=self.rfile.read(min(int(self.headers.get('Content-Length','0')),8193))
            if self.path!=state['path'] or body!=state['body'] or self.headers.get('Cookie') or self.headers.get('Authorization'):state['bad']+=1
            mode=state['mode']
            if mode=='dropped':self.connection.shutdown(socket.SHUT_RDWR);self.connection.close();return
            value=mode!='rejected'
            payload=json.dumps({state['field']:value}).encode()
            if mode=='echo':payload=json.dumps({state['field']:True,'passphrase':'never-return-this'}).encode()
            if mode=='duplicate':payload=(' {"'+state['field']+'":false,"'+state['field']+'":true}').encode()
            self.send_response(302 if mode=='redirect' else state['status'])
            if mode=='redirect':self.send_header('Location','http://127.0.0.1:8001/canary')
            self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
    reports=[];origin='http://127.0.0.1:8000'
    with server(Canary,8001),server(Endpoint,8000):
        for operation in (FormOperation.LOGIN,FormOperation.SEARCH):
            login=operation==FormOperation.LOGIN
            fields=('account','passphrase') if login else ('term',)
            form=InteractiveFormContract('a'*32,'b'*64,operation,
                (SecretReference('LOCAL_ACCOUNT'),SecretReference('LOCAL_CODE')) if login else (SecretReference('LOCAL_TERM'),),
                ElementMapping('login.accepted' if login else 'search.results',(LocatorSpec(LocatorStrategy.TEST_ID,'result'),)))
            binding=LocalFormBinding(form,origin+('/account/access' if login else '/catalog/find'),
                origin+('/session/check' if login else '/v2/query'),fields,
                LocalBooleanResponse(201 if login else 200,'authenticated' if login else 'hasResults',True),
                LocalBooleanResponse(403 if login else 200,'authenticated' if login else 'hasResults',False))
            project=ProjectConfig('a'*32,'Owned reusable proof',binding.document_url,('127.0.0.1',),True)
            values=('fixture-user','fixture-only') if login else ('paper & pens',)
            state['body']=urlencode(tuple(zip(fields,values,strict=True))).encode();state['path']=binding.endpoint_url[len(origin):]
            state['field']=binding.accepted.field_name
            modes=('accepted','rejected','echo','duplicate','redirect','dropped') if login else ('accepted','rejected')
            for mode in modes:
                state['mode']=mode;state['status']=binding.rejected.status_code if mode=='rejected' else binding.accepted.status_code
                transport=OwnedSubmissionTransport(binding,project,current_fingerprint='b'*64)
                request=dict(url=binding.endpoint_url,method='POST',content_type=CONTENT_TYPE,body=state['body'])
                before=state['posts'];result=transport.submit(**request)
                assert result.outcome==(mode if mode in ('accepted','rejected') else 'error'),(mode,result)
                assert result.attempted_submissions==(None if mode=='dropped' else 1)
                assert transport.submit(**request).outcome=='blocked' and state['posts']==before+1
                assert 'never-return-this' not in repr(result)
                reports.append(dict(operation=operation.value,mode=mode,outcome=result.outcome,attempted_submissions=result.attempted_submissions))
    assert state['posts']==8 and state['bad']==state['canary']==0
    output=Path('artifacts/interactive-probe/reusable-local.json');output.parent.mkdir(parents=True,exist_ok=True)
    report=dict(owned_loopback_only=True,fixed_fixture_registry_required=False,browser_integrated=False,
        scenarios=reports,posts=state['posts'],canary_contacts=state['canary'],bad_requests=state['bad'],retries=0)
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(scenarios=len(reports),posts=8,canary_contacts=0,bad_requests=0)))


if __name__=='__main__':main()
