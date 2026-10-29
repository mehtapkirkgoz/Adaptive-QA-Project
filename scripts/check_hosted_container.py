"""CI-only Linux container/TLS proof using disposable accounts and private Docker resources."""
import http.client,json,os,socket,ssl,subprocess,time
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
from http.cookiejar import CookieJar
from urllib.request import Request


def main():
    if os.environ.get('GITHUB_ACTIONS')!='true':raise ValueError('This proof runs only on disposable CI runners.')
    prefix='adaptive-qa-proof-'+uuid4().hex[:12];network=prefix+'-net';volume=prefix+'-data';app=prefix+'-app';proxy=prefix+'-proxy'
    image='adaptive-qa-server:ci';created=[]
    def docker(*args,**kwargs):
        return subprocess.check_output(['docker',*args],text=True,timeout=kwargs.pop('timeout',120),**kwargs).strip()
    with TemporaryDirectory(prefix='owned-hosted-container-') as directory:
        root=Path(directory)
        try:
            docker('network','create',network);created.append(('network',network))
            docker('volume','create',volume);created.append(('volume',volume))
            sandbox="from playwright.sync_api import sync_playwright; import os; assert os.geteuid()!=0; p=sync_playwright().start(); b=p.chromium.launch(chromium_sandbox=True,timeout=10000); b.close(); p.stop(); print('sandbox-ok')"
            security=['--cap-drop=ALL','--security-opt=no-new-privileges:true','--security-opt=seccomp='+str(Path('deploy/server/seccomp_profile.json').resolve()),'--read-only','--tmpfs','/tmp:rw,nosuid,nodev,size=512m,mode=1777','--shm-size=512m','--pids-limit=256','--memory=2g','--cpus=2','--init']
            assert 'sandbox-ok' in docker('run','--rm','--network=none',*security,'--entrypoint=python',image,'-c',sandbox)
            provision="from adaptive_qa.hosted import HostedSessions; from pathlib import Path; s=HostedSessions(Path('/data/auth.sqlite')); s.create_user('fixture@example.test','fixture-container-password'); print('provisioned')"
            docker('run','--rm','--network=none',*security,'-v',volume+':/data','--entrypoint=python',image,'-c',provision)
            docker('run','-d','--name',app,'--network',network,'--network-alias','app',*security,'-v',volume+':/data',image,'hosted','serve','--public-origin','https://qa.example.test');created.append(('container',app))
            config=root/'Caddyfile';config.write_text('''{
    local_certs
    admin off
}
https://qa.example.test {
    reverse_proxy app:8080 {
        header_up -X-Forwarded-*
        header_up -Forwarded
    }
}
''')
            docker('run','-d','--name',proxy,'--network',network,'-p','127.0.0.1:9443:443','-v',str(config)+':/etc/caddy/Caddyfile:ro','caddy:2');created.append(('container',proxy))
            ca=root/'root.crt';deadline=time.monotonic()+45
            while not ca.exists():
                try:docker('cp',proxy+':/data/caddy/pki/authorities/local/root.crt',str(ca))
                except subprocess.CalledProcessError:
                    if time.monotonic()>deadline:raise
                    time.sleep(.5)
            context=ssl.create_default_context(cafile=ca);context.keylog_filename=None;cookies=CookieJar()
            def request(method,path,body=None):
                connection=http.client.HTTPConnection('127.0.0.1',9443,timeout=5);connection.auto_open=0
                connection.sock=context.wrap_socket(socket.create_connection(('127.0.0.1',9443),timeout=5),server_hostname='qa.example.test')
                req=Request('https://qa.example.test'+path);cookies.add_cookie_header(req)
                headers={'Host':'qa.example.test','Connection':'close'}
                if req.get_header('Cookie'):headers['Cookie']=req.get_header('Cookie')
                if body is not None:
                    body=json.dumps(body).encode();headers.update({'Content-Type':'application/json','Origin':'https://qa.example.test'})
                    csrf=next((c.value for c in cookies if c.name=='adaptive_csrf'),None)
                    if csrf:headers['X-CSRF-Token']=csrf
                try:
                    connection.request(method,path,body=body,headers=headers);response=connection.getresponse();raw=response.read(1048577)
                    cookies.extract_cookies(response,req)
                    return response.status,raw,response.headers
                finally:connection.close()
            deadline=time.monotonic()+45
            while True:
                try:
                    status,_,_=request('GET','/api/runtime')
                    if status==200:break
                except (OSError,ssl.SSLError):pass
                if time.monotonic()>deadline:raise ValueError('Server did not become ready.')
                time.sleep(.5)
            status,_,headers=request('POST','/api/auth/login',dict(email='fixture@example.test',password='fixture-container-password'))
            assert status==200
            assert len(cookies)==2 and all(cookie.secure for cookie in cookies)
            assert all('SameSite=strict' in v for v in headers.get_all('Set-Cookie'))
            status,raw,_=request('GET','/api/auth/me');assert status==200 and json.loads(raw)['edition']=='hosted'
            status,_,_=request('POST','/api/site-checks',dict(url='http://127.0.0.1:8000/'));assert status==400
            status,_,_=request('GET','/api/local/license');assert status==404
            assert json.loads(docker('inspect','--format={{json .HostConfig.PortBindings}}',app))=={}
            docker('stop',app);backup=root/'backup';docker('cp',app+':/data',str(backup))
            import sqlite3
            from contextlib import closing
            with closing(sqlite3.connect(backup/'auth.sqlite')) as c:assert c.execute('SELECT count(*) FROM dashboard_users').fetchone()[0]==1
            assert b'fixture-container-password' not in (backup/'auth.sqlite').read_bytes()
            docker('start',app);deadline=time.monotonic()+30
            while True:
                try:
                    status,_,_=request('GET','/api/auth/me')
                    if status==200:break
                except OSError:pass
                if time.monotonic()>deadline:raise ValueError('Session/data did not survive restart.')
                time.sleep(.5)
            status,_,_=request('POST','/api/auth/logout',{});assert status==200
            status,_,_=request('GET','/api/auth/me');assert status==401
            result=dict(non_root=True,chromium_sandbox=True,https_verified_with_owned_ca=True,secure_cookies=True,
                authenticated_backend=True,private_targets_rejected=True,app_port_not_published=True,
                offline_backup_readable=True,restart_preserves_sessions=True,logout_revokes_session=True,
                public_activation=False,public_target_submissions=0,production_load_tested=False,
                application_image_id=docker('image','inspect','--format={{.Id}}',image))
            output=Path('artifacts/hosted');output.mkdir(parents=True,exist_ok=True)
            (output/'container.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
        except Exception:
            for kind,name in created:
                if kind=='container':
                    subprocess.run(['docker','logs','--tail','50',name],timeout=15,check=False)
            raise
        finally:
            for kind,name in reversed(created):
                subprocess.run(['docker',kind,'rm',*(['-f'] if kind=='container' else []),name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=30)


if __name__=='__main__':main()
