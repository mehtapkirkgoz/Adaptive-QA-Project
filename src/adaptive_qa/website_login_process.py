"""Single-use standard HTML login, pinned HTTPS, no scripts or stored credentials."""
from dataclasses import dataclass, replace
from html.parser import HTMLParser
from http.cookiejar import CookieJar
import http.client
import json
import os
import re
import ssl
import subprocess
import sys
import math
from threading import Thread
from time import monotonic
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import Request

from adaptive_qa.config import ProjectConfig
from adaptive_qa.egress import DestinationGuard
from adaptive_qa.interactive_probe import InteractiveProbeResult
from adaptive_qa.models import TestStatus


CASE_NAMES = {'LOGIN-FORM':'Login form and HTTPS destination',
    'LOGIN-IDENTIFIER':'Empty identifier requires a value', 'LOGIN-PASSWORD':'Empty password requires a value',
    'LOGIN-ACCOUNT':'Test account signs in', 'LOGIN-LOGOUT':'Sign out and verify protected access is removed'}
REASONS = {'standard_form', 'required_declared', 'required_missing', 'authenticated_markers',
    'credentials_rejected', 'outcome_uncertain', 'unsupported_form', 'unsupported_authentication',
    'logout_unavailable', 'logout_verified', 'logout_unverified', 'transport_error',
    'deadline_exceeded', 'cancelled', 'child_failed'}


class Unsupported(ValueError):
    pass


def scoped_url(raw, base):
    url = urljoin(base, raw)
    p, b = urlsplit(url), urlsplit(base)
    if (p.scheme != 'https' or p.netloc != b.netloc or p.username or p.password
            or p.query or p.fragment or len(url) > 2048 or '\\' in url
            or any(ord(c) < 33 for c in url)):
        raise Unsupported('Only exact-origin HTTPS paths without queries are supported.')
    return url


class Document(HTMLParser):
    """No DOM execution, response/body export or hidden-value persistence."""
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.forms, self.links, self.current = [], [], None
        self.stack=[]; self.rejection=False
        self.unsupported = False
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        alert=(a.get('role')=='alert' or a.get('id')=='flash' or 'error' in a.get('class','').lower())
        if tag not in ('input','br','meta','link','img','hr','base','wbr','source','area','embed','param','track','col'):
            self.stack.append((tag,alert))
        if len(a) != len(attrs): self.unsupported = True
        if tag == 'base' or (tag == 'iframe'):
            self.unsupported = True
        if tag == 'form':
            if self.current is not None: self.unsupported = True
            self.current = dict(attrs=a, fields=[], buttons=[], button_text='')
            self.forms.append(self.current)
        if tag in ('input','button','select','textarea') and self.current is not None:
            if tag == 'input': self.current['fields'].append(a)
            elif tag == 'button':
                self.current['buttons'].append(a)
                self.in_button=True
            else: self.unsupported = True
        if tag == 'a' and 'href' in a: self.links.append(a['href'])
        if tag == 'input' and a.get('form'): self.unsupported = True
        if any('captcha' in str(v).lower() for k,v in attrs if k in ('id','class','name')):
            self.unsupported = True

    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==tag:self.stack=self.stack[:i];break
        if tag == 'form': self.current = None
        if tag == 'button': self.in_button=False

    def handle_data(self,data):
        if any(alert for _,alert in self.stack) and any(word in data.lower() for word in
                ('invalid credentials','incorrect password','invalid password','invalid username',
                 'incorrect username','authentication failed','your password is invalid','your username is invalid',
                 'invalid email or password')):
            self.rejection=True
        if self.current is not None and getattr(self,'in_button',False):
            self.current['button_text']=(self.current['button_text']+data)[:1024]

    def login(self, url):
        forms = [f for f in self.forms if any(x.get('type','text').lower()=='password' for x in f['fields'])]
        if self.unsupported or len(forms) != 1: raise Unsupported('No unique supported login form.')
        form = forms[0]; a = form['attrs']; fields = form['fields']
        if (a.get('method','get').lower() != 'post'
                or a.get('enctype','application/x-www-form-urlencoded').lower() != 'application/x-www-form-urlencoded'
                or a.get('target','') not in ('','_self') or 'hidden' in a
                or any(k.startswith('on') for k in a)):
            raise Unsupported('Only a native same-origin POST login is supported.')
        endpoint = scoped_url(a.get('action',''),url)
        passwords = [x for x in fields if x.get('type','text').lower()=='password']
        identifiers = [x for x in fields if x.get('type','text').lower() in ('text','email')]
        if len(passwords)!=1 or len(identifiers)!=1: raise Unsupported('Ambiguous fields.')
        password, identifier = passwords[0], identifiers[0]
        if password.get('autocomplete')=='new-password': raise Unsupported('Registration is not login.')
        intent=' '.join((a.get('id',''),a.get('name',''),form['button_text'],
            *(x.get('value','') for x in fields if x.get('type')=='submit'))).lower()
        if (any(w in intent for w in ('register','sign up','signup','reset','create account'))
                or password.get('autocomplete')!='current-password' and not any(w in intent for w in ('login','log in','signin','sign in','giriş','giris'))):
            raise Unsupported('A clear login form is required.')
        for field in fields:
            if (not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.:-]{0,99}',field.get('name',''))
                    or any(k in field for k in ('disabled','readonly','formaction','formmethod','formtarget','formenctype','form'))
                    or any(k.startswith('on') for k in field)
                    or field.get('type','text').lower() not in ('text','email','password','hidden','submit')):
                raise Unsupported('Unsupported form control.')
        names=[x['name'] for x in fields]
        if len(names)!=len(set(names)) or len(fields)>20: raise Unsupported('Ambiguous field names.')
        if any(any(k in b for k in ('formaction','formmethod','formtarget','formenctype','name')) for b in form['buttons']):
            raise Unsupported('Unsupported submit override.')
        hidden=[(x['name'],x.get('value','')) for x in fields if x.get('type','').lower()=='hidden']
        if any(len(v)>2048 for _,v in hidden): raise Unsupported('Oversized hidden field.')
        kind='email' if identifier.get('type','text').lower()=='email' or 'email' in identifier['name'].lower() else 'username'
        return endpoint, identifier, password, hidden, kind

    def logout(self,url):
        found=[]
        for raw in self.links:
            try: value=scoped_url(raw,url)
            except ValueError: continue
            if re.fullmatch(r'.*/(?:logout|log-out|signout|sign-out)/?',urlsplit(value).path,re.I):
                found.append(value)
        found=set(found)
        return next(iter(found)) if len(found)==1 else None


class Transport:
    def __init__(self,url):
        self.base=url; self.cookies=CookieJar(); self.posted=False; self.attempted=0
        host=urlsplit(url).hostname
        self.guard=DestinationGuard(ProjectConfig('website-login','Website login',url,(host,),True),max_requests=16)
        self.target=None

    def close(self): self.cookies.clear()

    def request(self,method,url,body=None):
        scoped_url(url,self.base)
        if method not in ('GET','POST') or (method=='GET' and body is not None): raise Unsupported()
        if method=='POST':
            if self.posted: raise Unsupported('No duplicate submission.')
            self.posted=True
        if self.target is None:
            target=self.guard.authorize(url)
            self.target=replace(target,addresses=(target.addresses[0],))
        else:
            self.guard.requests+=1
            if self.guard.requests>16: raise Unsupported('Request budget consumed.')
        target=self.target
        connection=http.client.HTTPConnection(target.hostname,target.port,timeout=5)
        connection.auto_open=0
        try:
            connection.sock=self.guard.connect(target,timeout_seconds=5)
            context=ssl.create_default_context(); context.keylog_filename=None
            connection.sock=context.wrap_socket(connection.sock,server_hostname=target.hostname)
            connection.sock.settimeout(5)
            req=Request(url); self.cookies.add_cookie_header(req)
            headers={'Host':target.hostname,'Accept':'text/html','Connection':'close',
                     'User-Agent':'Adaptive-QA-Authorized-Login/1.0'}
            if req.get_header('Cookie'): headers['Cookie']=req.get_header('Cookie')
            if method=='POST':
                headers.update({'Content-Type':'application/x-www-form-urlencoded','Content-Length':str(len(body)),
                                'Origin':'https://'+urlsplit(self.base).netloc,'Referer':self.base})
                self.attempted=1
            connection.request(method,urlsplit(url).path or '/',body=body,headers=headers)
            response=connection.getresponse()
            if response.getheader('Content-Encoding') or len(response.headers.get_all('Location',[]))>1: raise Unsupported()
            raw=response.read(262145)
            if len(raw)>262144: raise Unsupported('Response too large.')
            self.cookies.extract_cookies(response,req)
            status=response.status; location=response.getheader('Location')
            if location:
                if status not in (302,303):
                    raise Unsupported('Unsupported redirect protocol.')
                return status, scoped_url(location,url), ''
            if status not in (200,401,403) or 'text/html' not in response.getheader('Content-Type','').lower():
                raise Unsupported('Expected an HTML document.')
            return status,None,raw.decode('utf-8','strict')
        finally: connection.close()

    def read(self,url):
        for _ in range(4):
            status,location,html=self.request('GET',url)
            if location: url=location; continue
            return url,status,Document(html)
        raise Unsupported('Redirect budget consumed.')


def case(name,status,reason): return dict(case_id=name,status=status,reason_code=reason)


def execute(url,kind,identifier,password,transport_factory=Transport):
    transport=transport_factory(url); results=[]
    try:
        login_url,status,document=transport.read(url)
        endpoint,user,pwd,hidden,observed_kind=document.login(login_url)
        if status!=200 or kind!=observed_kind or document.logout(login_url): raise Unsupported('Login form changed or already ambiguous.')
        results.append(case('LOGIN-FORM','passed','standard_form'))
        for name,field in (('LOGIN-IDENTIFIER',user),('LOGIN-PASSWORD',pwd)):
            required='required' in field
            results.append(case(name,'passed' if required else 'not_run','required_declared' if required else 'required_missing'))
        body=urlencode(hidden+[(user['name'],identifier),(pwd['name'],password)]).encode('ascii')
        status,location,html=transport.request('POST',endpoint,body)
        final_url,status,after=transport.read(location) if location else (endpoint,status,Document(html))
        logout=after.logout(final_url)
        has_password=any(any(f.get('type','text').lower()=='password' for f in form['fields']) for form in after.forms)
        if status!=200 or not logout or has_password or not transport.cookies or final_url==login_url:
            # A generic HTTP 200 or a missing password field alone never proves authentication.
            rejected=has_password and after.rejection
            results.append(case('LOGIN-ACCOUNT','failed' if rejected else 'not_run','credentials_rejected' if rejected else 'outcome_uncertain'))
            results.append(case('LOGIN-LOGOUT','not_run','logout_unavailable'))
        else:
            results.append(case('LOGIN-ACCOUNT','passed','authenticated_markers'))
            _,logout_status,out=transport.read(logout)
            _,protected_status,protected=transport.read(final_url)
            try: out.login(login_url); protected.login(login_url); verified=logout_status==200 and protected_status==200
            except Unsupported: verified=False
            results.append(case('LOGIN-LOGOUT','passed' if verified else 'not_run','logout_verified' if verified else 'logout_unverified'))
        return dict(cases=results,attempted_submissions=transport.attempted)
    except Unsupported:
        existing={r['case_id'] for r in results}
        results.extend(case(c,'not_run','unsupported_form' if transport.attempted==0 else 'outcome_uncertain') for c in CASE_NAMES if c not in existing)
        return dict(cases=results,attempted_submissions=transport.attempted)
    except Exception:
        return dict(cases=[case(c,'error','transport_error') for c in CASE_NAMES],attempted_submissions=None if transport.attempted else 0)
    finally: transport.close()


def validate_result(data):
    if not isinstance(data,dict) or set(data)!={'cases','attempted_submissions'}: raise ValueError('Invalid login result.')
    if data['attempted_submissions'] is not None and (type(data['attempted_submissions']) is not int or data['attempted_submissions'] not in (0,1)): raise ValueError()
    rows=data['cases']
    if not isinstance(rows,list) or len(rows)!=len(CASE_NAMES) or {r.get('case_id') for r in rows if isinstance(r,dict)}!=set(CASE_NAMES): raise ValueError()
    for r in rows:
        if set(r)!={'case_id','status','reason_code'} or r['status'] not in ('passed','failed','error','not_run','cancelled') or r['reason_code'] not in REASONS: raise ValueError()
    return data


@dataclass(frozen=True)
class WebsiteLoginResult(InteractiveProbeResult):
    cases: tuple = ()


def result_object(data):
    validate_result(data)
    rows=data['cases']
    status=TestStatus.CANCELLED if any(c['status']=='cancelled' for c in rows) else TestStatus.ERROR if any(c['status']=='error' for c in rows) else TestStatus.FAILED if any(c['status']=='failed' for c in rows) else TestStatus.PASSED if all(c['status']=='passed' for c in rows) else TestStatus.BLOCKED
    return WebsiteLoginResult(status,'Website login results.',data['attempted_submissions'],tuple(rows))


def run_login(review,identifier,password,*,should_cancel,timeout_seconds=45):
    from adaptive_qa.browser_process import _terminate_process_tree
    from adaptive_qa.website_login import SavedWebsiteLoginReview
    if (not isinstance(review,SavedWebsiteLoginReview) or not callable(should_cancel)
            or isinstance(timeout_seconds,bool) or not isinstance(timeout_seconds,(int,float))
            or not math.isfinite(timeout_seconds) or not 0<timeout_seconds<=45): raise ValueError()
    for value in (identifier,password):
        if not isinstance(value,str) or not 1<=len(value)<=512 or any(ord(c)<32 or ord(c)==127 for c in value): raise ValueError('Use bounded test credentials.')
    reason='child_failed'; process=None; writer=None; started=monotonic()
    try:
        if should_cancel(): reason='cancelled'; raise InterruptedError()
        options={'creationflags':subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP} if os.name=='nt' else {'start_new_session':True}
        # Credentials travel on an anonymous pipe, never command arguments, files or the environment.
        process=subprocess.Popen([sys.executable,'-m','adaptive_qa.website_login_process'],stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,**options)
        raw=json.dumps(dict(url=review.document_url,kind=review.identifier_kind,identifier=identifier,password=password)).encode()
        if len(raw)>8192:raise ValueError('Oversized credential input.')
        def send():
            try:process.stdin.write(raw)
            except OSError:pass
            finally:process.stdin.close()
        writer=Thread(target=send,daemon=True);writer.start()
        while process.poll() is None:
            if should_cancel(): reason='cancelled'; raise InterruptedError()
            if monotonic()-started>=timeout_seconds: reason='deadline_exceeded'; raise TimeoutError()
            try: process.wait(timeout=.1)
            except subprocess.TimeoutExpired: pass
        if process.returncode!=0: raise ValueError()
        if monotonic()-started>=timeout_seconds:reason='deadline_exceeded';raise TimeoutError()
        raw=process.stdout.read(4097)
        if len(raw)>4096: raise ValueError()
        if should_cancel(): reason='cancelled'; raise InterruptedError()
        return result_object(json.loads(raw))
    except Exception:
        return result_object(dict(cases=[case(c,'cancelled' if reason=='cancelled' else 'error',reason) for c in CASE_NAMES],attempted_submissions=None if process else 0))
    finally:
        if process is not None:
            if process.poll() is None: _terminate_process_tree(process)
            if writer:writer.join(timeout=1)
            if process.stdout: process.stdout.close()


def main():
    raw=sys.stdin.buffer.read(8193)
    if len(raw)>8192: raise ValueError()
    data=json.loads(raw)
    if set(data)!={'url','kind','identifier','password'}: raise ValueError()
    scoped_url(data['url'],data['url'])
    for value in (data['identifier'],data['password']):
        if not isinstance(value,str) or not 1<=len(value)<=512: raise ValueError()
    result=execute(data['url'],data['kind'],data['identifier'],data['password'])
    sys.stdout.write(json.dumps(validate_result(result)))


if __name__=='__main__': main()
