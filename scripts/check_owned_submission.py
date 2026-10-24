"""Pinned one-shot local endpoint proof, with no browser or customer credentials."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from pathlib import Path
import json
import socket

from adaptive_qa.config import ProjectConfig
from adaptive_qa.element_models import ElementMapping, LocatorSpec, LocatorStrategy
from adaptive_qa.interactive_contracts import FormOperation, InteractiveFormContract
from adaptive_qa.owned_submission import CONTENT_TYPE, ORIGIN, OwnedSubmissionContract, OwnedSubmissionTransport
from adaptive_qa.secrets import SecretReference


@contextmanager
def server(handler, port):
    instance=ThreadingHTTPServer(("127.0.0.1",port),handler)
    thread=Thread(target=instance.serve_forever,daemon=True);thread.start()
    try:yield instance
    finally:instance.shutdown();instance.server_close();thread.join(timeout=5)


def main():
    state={"mode":"accepted","posts":0,"other":0,"canary":0,"bad_shape":0}
    class Canary(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            state["canary"]+=1;self.send_response(200);self.end_headers()
    class Fixture(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            state["other"]+=1;self.send_response(405);self.end_headers()
        def do_POST(self):
            state["posts"]+=1
            length=int(self.headers.get("Content-Length","0"))
            body=self.rfile.read(min(length,8193))
            if (self.path!="/interactive-submit/login-transition" or body!=b"user=fixture&password=fixture-only"
                    or self.headers.get("Content-Type")!=CONTENT_TYPE
                    or self.headers.get("Cookie") or self.headers.get("Authorization")):
                state["bad_shape"]+=1
            mode=state["mode"]
            if mode=="dropped":
                self.connection.shutdown(socket.SHUT_RDWR);self.connection.close();return
            payload=b'{"outcome":"accepted"}' if mode=="accepted" else b'{"outcome":"rejected"}'
            if mode=="malformed":payload=b'{"password":"must-not-be-returned"}'
            self.send_response(302 if mode=="redirect" else 401 if mode=="rejected" else 200)
            if mode=="redirect":self.send_header("Location","http://127.0.0.1:8001/canary")
            self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(payload)))
            self.end_headers();self.wfile.write(payload)
    form=InteractiveFormContract("a"*32,"b"*64,FormOperation.LOGIN,
        (SecretReference("UNRESOLVED_FIXTURE_USER"),SecretReference("UNRESOLVED_FIXTURE_PASSWORD")),
        ElementMapping("login.accepted",(LocatorSpec(LocatorStrategy.TEST_ID,"result"),)))
    contract=OwnedSubmissionContract(form,"login-transition",ORIGIN+"/interactive/login-transition",
        ORIGIN+"/interactive-submit/login-transition",("user","password"))
    project=ProjectConfig("a"*32,"Owned submission proof",contract.document_url,("127.0.0.1",),True)
    reports=[]
    with server(Canary,8001),server(Fixture,8000):
        for mode,expected in (("accepted","accepted"),("rejected","rejected"),("redirect","error"),
                              ("malformed","error"),("dropped","error")):
            state["mode"]=mode
            transport=OwnedSubmissionTransport(contract,project,current_fingerprint="b"*64)
            request=dict(url=contract.endpoint_url,method="POST",content_type=CONTENT_TYPE,body=b"user=fixture&password=fixture-only")
            before=state["posts"];result=transport.submit(**request)
            assert result.outcome==expected,(mode,result)
            assert result.attempted_submissions==(None if mode=="dropped" else 1)
            assert transport.submit(**request).outcome=="blocked"
            assert state["posts"]==before+1
            assert "must-not-be-returned" not in repr(result)
            reports.append(dict(scenario=mode,outcome=result.outcome,attempted_submissions=result.attempted_submissions))
    assert state["posts"]==5 and state["other"]==state["canary"]==state["bad_shape"]==0,state
    report=dict(owned_fixture_only=True,scenarios=reports,contacts={key:state[key] for key in ("posts","other","canary","bad_shape")},
                redirects_followed=0,retries=0,browser_integrated=False)
    output=Path("artifacts/interactive-probe/owned-submission.json");output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report))


if __name__=="__main__":main()
