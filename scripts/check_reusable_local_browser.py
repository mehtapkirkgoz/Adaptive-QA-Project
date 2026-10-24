"""Supervised reusable local browser forms with independently configured bindings."""
from http.server import BaseHTTPRequestHandler
from pathlib import Path
import json
import os
import socket
from unittest.mock import patch
from urllib.parse import urlencode
from check_owned_submission import server
from adaptive_qa.config import ProjectConfig
from adaptive_qa.element_models import ElementMapping,LocatorSpec,LocatorStrategy,ProjectElementMappings
from adaptive_qa.interactive_contracts import FormOperation,InteractiveFormContract
from adaptive_qa.local_form_binding import LocalFormBinding,LocalBooleanResponse
from adaptive_qa.interactive_process import run_isolated_local_form
from adaptive_qa.secrets import SecretReference


def main():
    state=dict(mode='accepted',documents=0,posts=0,canary=0,bad=0,binding=None,body=b'')
    class Canary(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):state['canary']+=1;self.send_error(403)
    class Fixture(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            binding=state['binding'];mode=state['mode']
            if self.path!=binding.document_url.removeprefix('http://127.0.0.1:8000'):state['bad']+=1;self.send_error(404);return
            state['documents']+=1;login=binding.form.operation==FormOperation.LOGIN
            controls=('<label>Member ID<input name="identity"></label><label>Access code<input name="accessCode" type="password"></label><button>Enter area</button>'
                if login else '<label>Lookup text<input name="keywords" type="search"></label><button>Locate items</button>')
            if mode=='wrong-field':controls=controls.replace('name="identity"','name="other"')
            action='http://127.0.0.1:8001/canary' if mode=='wrong-action' else binding.endpoint_url
            document='<meta charset="utf-8"><form method="post" action="'+action+'">'+controls+'</form>'
            document+='<div data-testid="confirmed"'+('' if mode=='preexisting' else ' hidden')+'>Ready</div><div data-testid="denied" hidden>Unavailable</div>'
            send="fetch(form.action,{method:'POST',body:new URLSearchParams(new FormData(form))})"
            field=binding.accepted.field_name
            script="const form=document.querySelector('form');form.addEventListener('submit',e=>{e.preventDefault();"
            if mode=='fake-marker':script+="document.querySelector('[data-testid=confirmed]').hidden=false;"
            else:
                script+=send+".then(r=>r.json()).then(d=>{"
                if mode!='no-marker':script+="document.querySelector('[data-testid='+ (d."+field+"?'confirmed':'denied') +']').hidden=false;"
                script+="}).catch(()=>{});"
                if mode=='duplicate':script+=send+".catch(()=>{});"
            script+="});"
            if mode=='canary':script+="form.querySelector('input').addEventListener('input',()=>fetch('http://127.0.0.1:8001/canary').catch(()=>{}));"
            raw=(document+'<script>'+script+'</script>').encode()
            self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        def do_POST(self):
            binding=state['binding'];mode=state['mode'];state['posts']+=1
            raw=self.rfile.read(min(int(self.headers.get('Content-Length','0')),8193))
            if self.path!=binding.endpoint_url.removeprefix('http://127.0.0.1:8000') or raw!=state['body']:state['bad']+=1
            if mode=='dropped':self.connection.shutdown(socket.SHUT_RDWR);self.connection.close();return
            response=binding.rejected if mode=='rejected' else binding.accepted
            raw=json.dumps({response.field_name:response.expected_value}).encode()
            self.send_response(302 if mode=='redirect' else response.status_code)
            if mode=='redirect':self.send_header('Location','http://127.0.0.1:8001/canary')
            self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    reports=[];origin='http://127.0.0.1:8000'
    with server(Canary,8001),server(Fixture,8000),patch.dict(os.environ,{'REUSABLE_USER':'fixture-member','REUSABLE_CODE':'fixture-code','REUSABLE_TERM':'paper & pens'}):
        for login in (True,False):
            cases=[('accepted','passed',1),('rejected','passed',1)]
            if login:cases += [('wrong-field','blocked',0),('wrong-action','blocked',0),('preexisting','blocked',0),
                ('canary','error',0),('fake-marker','error',0),('no-marker','failed',1),('duplicate','error',1),('redirect','error',1),('dropped','error',1)]
            for mode,status,posts in cases:
                operation=FormOperation.LOGIN if login else FormOperation.SEARCH;negative=mode=='rejected'
                form=InteractiveFormContract('a'*32,'b'*64,operation,
                    (SecretReference('REUSABLE_USER'),SecretReference('REUSABLE_CODE')) if login else (SecretReference('REUSABLE_TERM'),),
                    ElementMapping(('login.rejected' if negative else 'login.accepted') if login else ('search.empty' if negative else 'search.results'),
                        (LocatorSpec(LocatorStrategy.TEST_ID,'denied' if negative else 'confirmed'),)),5)
                binding=LocalFormBinding(form,origin+('/portal/access' if login else '/store/lookup'),origin+('/auth/check' if login else '/search/resolve'),
                    ('identity','accessCode') if login else ('keywords',),
                    LocalBooleanResponse(201 if login else 200,'sessionReady' if login else 'matchesFound',True),
                    LocalBooleanResponse(403 if login else 200,'sessionReady' if login else 'matchesFound',False))
                mapping_data=(('login.username','Member ID',None),('login.password','Access code',None),('login.submit','Enter area','button')) if login else (('search.query','Lookup text',None),('search.submit','Locate items','button'))
                mappings=ProjectElementMappings('a'*32,tuple(ElementMapping(key,(LocatorSpec(LocatorStrategy.ROLE if role else LocatorStrategy.LABEL,label,role),)) for key,label,role in mapping_data))
                project=ProjectConfig('a'*32,'Reusable owned browser',binding.document_url,('127.0.0.1',),True)
                state['binding']=binding;state['mode']=mode
                values=('fixture-member','fixture-code') if login else ('paper & pens',)
                state['body']=urlencode(tuple(zip(binding.field_names,values,strict=True))).encode()
                before=state['posts'];result=run_isolated_local_form(binding,project,current_fingerprint='b'*64,mappings=mappings,timeout_seconds=20)
                assert result.status.value==status,(mode,result)
                assert state['posts']==before+posts,(mode,state['posts'],before)
                assert result.attempted_submissions is None if mode=='dropped' else result.attempted_submissions==posts
                assert 'fixture-code' not in repr(result)
                reports.append(dict(operation=operation.value,mode=mode,status=status,endpoint_posts=posts,attempted_submissions=result.attempted_submissions))
    assert state['canary']==state['bad']==0
    report=dict(owned_loopback_only=True,fixture_registry_required=False,scenarios=reports,
        contacts={key:state[key] for key in ('documents','posts','canary','bad')},screenshots=0)
    output=Path('artifacts/interactive-probe/reusable-browser.json');output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(scenarios=len(reports),contacts=report['contacts'])))


if __name__=='__main__':main()
