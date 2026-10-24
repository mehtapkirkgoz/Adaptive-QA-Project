"""Supervised Chromium POSTs only to owned fixed endpoints; no external activation."""
from http.server import BaseHTTPRequestHandler
from pathlib import Path
import json
import os
import socket
from threading import Event
from unittest.mock import patch
from urllib.parse import parse_qs

from check_owned_submission import server
from adaptive_qa.config import ProjectConfig
from adaptive_qa.element_models import ElementMapping,LocatorSpec,LocatorStrategy
from adaptive_qa.interactive_contracts import FormOperation,InteractiveFormContract
from adaptive_qa.interactive_fixtures import fixture_document,FIXTURES
from adaptive_qa.interactive_process import run_isolated_interactive_probe
from adaptive_qa.secrets import SecretReference


def main():
    state=dict(mode="normal",documents=0,posts=0,canary=0,unexpected=0,bad_body=0)
    class Canary(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):state["canary"]+=1;self.send_error(403)
    class Fixture(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            fixture_id=self.path.removeprefix("/interactive/")
            if fixture_id not in FIXTURES:state["unexpected"]+=1;self.send_error(404);return
            state["documents"]+=1
            url="http://127.0.0.1:8000"+self.path
            document=fixture_document(fixture_id,url).split("<script>")[0]
            endpoint=url.replace("/interactive/","/interactive-submit/")
            document=document.replace('method="get"','method="post"').replace('action="'+url+'"','action="'+endpoint+'"')
            document=document.replace("Username","Email address").replace("Sign in","Log in").replace("Search products","Search query")
            if state["mode"]=="wrong-action":document=document.replace(endpoint,"http://127.0.0.1:8001/canary")
            if state["mode"]=="wrong-field":document=document.replace('name="user"','name="other"')
            send="fetch(form.action,{method:'POST',body:new URLSearchParams(new FormData(form))})"
            script="const form=document.querySelector('form');form.addEventListener('submit',e=>{e.preventDefault();"+send+".then(r=>r.json()).then(d=>{document.querySelector('[data-testid='+ (d.outcome==='accepted'?'result':'negative') +']').hidden=false;}).catch(()=>{});"
            if state["mode"]=="duplicate":script+=send+".catch(()=>{});"
            script+="});"
            if state["mode"]=="premature":script+="form.querySelector('input').addEventListener('input',()=>{"+send+".catch(()=>{});});"
            if state["mode"]=="canary":script+="form.querySelector('input').addEventListener('input',()=>fetch('http://127.0.0.1:8001/canary').catch(()=>{}));"
            if state["mode"]=="altered-value":script=script.replace("e.preventDefault();","e.preventDefault();form.querySelector('input').value='changed';")
            body=(document+"<script>"+script+"</script>").encode()
            self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
        def do_POST(self):
            state["posts"]+=1
            fixture_id=self.path.removeprefix("/interactive-submit/")
            body=self.rfile.read(min(int(self.headers.get("Content-Length","0")),8193))
            fields=parse_qs(body.decode(),strict_parsing=True)
            expected={"query":["fixture-query"]} if fixture_id.startswith("search") else {"user":["fixture-user"],"password":["fixture-password"]}
            if fields!=expected or self.headers.get("Cookie") or self.headers.get("Authorization"):state["bad_body"]+=1
            if state["mode"]=="cancelled-post":release.wait(timeout=10);return
            if state["mode"]=="dropped":self.connection.shutdown(socket.SHUT_RDWR);self.connection.close();return
            negative=fixture_id in ("login-rejected","search-empty")
            payload=b'{"outcome":"rejected"}' if negative else b'{"outcome":"accepted"}'
            if state["mode"]=="malformed":payload=b'{"password":"never-return-this"}'
            self.send_response(302 if state["mode"]=="redirect" else 401 if negative else 200)
            if state["mode"]=="redirect":self.send_header("Location","http://127.0.0.1:8001/canary")
            self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(payload)));self.end_headers();self.wfile.write(payload)
    release=Event()
    reports=[]
    cases=[(fixture,"normal","passed",1) for fixture in ("login-transition","login-rejected","search-transition","search-empty")]
    cases += [("login-transition",mode,status,posts) for mode,status,posts in (
        ("wrong-action","blocked",0),("wrong-field","blocked",0),("premature","error",0),
        ("canary","error",0),("altered-value","error",0),("redirect","error",1),("malformed","error",1),("dropped","error",1),("duplicate","error",1),("cancelled-post","cancelled",1))]
    with server(Canary,8001),server(Fixture,8000),patch.dict(os.environ,{
            "OWNED_USER":"fixture-user","OWNED_PASSWORD":"fixture-password","OWNED_QUERY":"fixture-query"}):
        for fixture,mode,status,posts in cases:
            state["mode"]=mode;before=state["posts"]
            operation=FIXTURES[fixture];negative=fixture in ("login-rejected","search-empty")
            logical=("login.rejected" if negative else "login.accepted") if operation==FormOperation.LOGIN else ("search.empty" if negative else "search.results")
            inputs=(SecretReference("OWNED_USER"),SecretReference("OWNED_PASSWORD")) if operation==FormOperation.LOGIN else (SecretReference("OWNED_QUERY"),)
            contract=InteractiveFormContract("a"*32,"b"*64,operation,inputs,
                ElementMapping(logical,(LocatorSpec(LocatorStrategy.TEST_ID,"negative" if negative else "result"),)),5)
            project=ProjectConfig("a"*32,"Owned browser submission","http://127.0.0.1:8000/interactive/"+fixture,("127.0.0.1",),True)
            result=run_isolated_interactive_probe(contract,project,fixture_id=fixture,current_fingerprint="b"*64,
                fixture_source="owned_submission",timeout_seconds=20,
                should_cancel=(lambda:state["posts"]>before) if mode=="cancelled-post" else None)
            if mode=="cancelled-post":release.set()
            assert result.status.value==status,(fixture,mode,result)
            assert state["posts"]-before==posts,(mode,state)
            assert result.attempted_submissions is None if mode in ("dropped","cancelled-post") else result.attempted_submissions in (0,1)
            assert not any(value in repr(result) for value in ("fixture-password","never-return-this"))
            reports.append(dict(fixture=fixture,mode=mode,status=result.status.value,endpoint_posts=posts,attempted_submissions=result.attempted_submissions))
        # Exercise the saved owner-scoped queue and real worker, not just the probe API.
        from tempfile import TemporaryDirectory
        from adaptive_qa.local_free import LocalFreeProjects,LOCAL_ACTOR
        from adaptive_qa.project_settings import reference_name
        from adaptive_qa.interactive_review import review_saved_interactive
        from adaptive_qa.interactive_queue import OwnedInteractiveQueue,process_owned_interactive_once
        state["mode"]="normal"
        with TemporaryDirectory(prefix="owned-interactive-queue-") as temporary:
            projects=LocalFreeProjects(Path(temporary)/"projects.sqlite")
            saved_project=projects.create(LOCAL_ACTOR,"Owned queue proof")
            references={slot:reference_name(LOCAL_ACTOR.user_id,saved_project.project_id,slot) for slot in ("login_username","login_password")}
            projects.save_configuration(LOCAL_ACTOR,saved_project.project_id,dict(
                base_url="http://127.0.0.1:8000/interactive/login-transition",allowed_hosts=["127.0.0.1"],
                allow_data_changes=True,secret_references=references))
            queue=OwnedInteractiveQueue(projects)
            review=review_saved_interactive(projects,LOCAL_ACTOR,saved_project.project_id,fixture_id="login-transition",
                completion=ElementMapping("login.accepted",(LocatorSpec(LocatorStrategy.TEST_ID,"result"),)),timeout_seconds=5)
            job=queue.submit(LOCAL_ACTOR,review)
            before=state["posts"]
            with patch.dict(os.environ,{references["login_username"]:"fixture-user",references["login_password"]:"fixture-password"}):
                assert process_owned_interactive_once(queue)["status"]=="completed"
            result=queue.get(LOCAL_ACTOR,saved_project.project_id,job["job_id"])
            assert result["result"]==dict(status="passed",attempted_submissions=1),result
            assert state["posts"]==before+1
            assert b"fixture-password" not in projects.database.read_bytes()
            assert queue.claim_next() is None
            saved_queue_proof=dict(status="completed",result="passed",endpoint_posts=1,no_plaintext_in_database=True)
    assert state["canary"]==state["unexpected"]==state["bad_body"]==0,state
    report=dict(owned_fixture_only=True,scenarios=reports,contacts={k:state[k] for k in ("documents","posts","canary","unexpected","bad_body")},screenshots=0,saved_queue_proof=saved_queue_proof)
    output=Path("artifacts/interactive-probe/browser-submission.json");output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"scenarios":len(reports),"contacts":report["contacts"]}))


if __name__=="__main__":main()
