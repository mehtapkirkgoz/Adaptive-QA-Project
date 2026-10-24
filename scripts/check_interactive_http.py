"""Owned HTTP document fixtures with pinned initial GET and zero network submissions."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
from threading import Lock,Thread

from adaptive_qa.interactive_fixtures import FIXTURES,fixture_document
from check_interactive_process import main as check_process


def main():
    contacts={'documents':0,'writes':0,'canary':0,'unexpected':0};lock=Lock()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            fixture_id=self.path.removeprefix('/interactive/')
            if self.server.server_port==8001:
                with lock:contacts['canary']+=1
                self.send_error(403);return
            if fixture_id not in FIXTURES:
                with lock:contacts['unexpected']+=1
                self.send_error(404);return
            with lock:contacts['documents']+=1
            document=fixture_document(fixture_id,'http://127.0.0.1:8000/interactive/'+fixture_id)
            document=document.replace('Username','Email address').replace('Sign in','Log in').replace('Search products','Search query').replace('<button>Search</button>','<button>Find</button>')
            document=document.replace('https://example.invalid/denied','http://127.0.0.1:8001/denied')
            body=document.encode('utf-8')
            self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers()
            self.wfile.write(body)
        def do_POST(self):
            with lock:contacts['writes']+=1
            self.send_error(403)
        do_PUT=do_POST
        do_PATCH=do_POST
        do_DELETE=do_POST
        do_HEAD=do_POST
        do_OPTIONS=do_POST
    with ThreadingHTTPServer(('127.0.0.1',8000),Handler) as fixture,ThreadingHTTPServer(('127.0.0.1',8001),Handler) as canary:
        threads=[Thread(target=server.serve_forever,daemon=True) for server in (fixture,canary)]
        for thread in threads:thread.start()
        try:
            check_process('owned_http')
            assert 6<=contacts['documents']<=8 and contacts['writes']==contacts['canary']==contacts['unexpected']==0,contacts
        finally:
            fixture.shutdown();canary.shutdown()
            for thread in threads:thread.join(timeout=5);assert not thread.is_alive()
    output=Path('artifacts/interactive-probe/http-process.json')
    report=json.loads(output.read_text(encoding='utf-8'));report['owned_http_contacts']=contacts
    report['initial_document_pinned']=True;report['contrasting_control_names']=True
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'owned_http_documents':contacts['documents'],'network_submissions':contacts['writes'],'canary_contacts':contacts['canary']}))


if __name__=='__main__':main()
