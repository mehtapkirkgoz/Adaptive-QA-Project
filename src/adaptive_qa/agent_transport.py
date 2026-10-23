"""Signed bounded loopback coordinator/client for the controlled outbound pilot."""

import asyncio
import base64
import hmac
import http.client
import json
import re
import socket
from threading import Timer
from time import monotonic
from urllib.parse import urlsplit

from fastapi import FastAPI,Request
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse,Response

from adaptive_qa.agent_registry import (AGENT_PATHS,AgentAuthenticationError,
                                       message_signature,token_signing_key)
from adaptive_qa.secrets import SecretValue
from adaptive_qa.project_store import _id
from adaptive_qa.web_app import _object


MAX_MESSAGE = 1024*1024


class AgentTransportError(ValueError):
    """Transport failures deliberately omit credentials, payloads and URLs."""


def validate_coordinator(origin):
    if not isinstance(origin,str) or len(origin)>64:
        raise ValueError('A numeric loopback coordinator origin is required.')
    try:
        parsed = urlsplit(origin)
        port = parsed.port
        if type(port) is not int or not 1024<=port<=65535 or origin!=f'http://127.0.0.1:{port}':
            raise ValueError()
    except ValueError:
        raise ValueError('A numeric loopback coordinator origin is required.') from None
    return port


def create_agent_coordinator(broker,*,port):
    validate_coordinator(f'http://127.0.0.1:{port}')
    authority = f'127.0.0.1:{port}'.encode()
    app = FastAPI(docs_url=None,redoc_url=None,openapi_url=None)

    @app.exception_handler(AgentAuthenticationError)
    async def unauthenticated(request,error):
        return JSONResponse({'detail':'Agent request rejected.'},status_code=401)

    @app.exception_handler(ValueError)
    async def invalid(request,error):
        return JSONResponse({'detail':'Agent request rejected.'},status_code=400)

    @app.post('/agent/{operation}')
    async def dispatch(operation:str,request:Request):
        path = request.url.path
        raw = await request.body()
        sequence_text = request.headers['x-agent-sequence']
        if not sequence_text.isascii() or not sequence_text.isdecimal() or len(sequence_text)>10:
            raise AgentAuthenticationError('Agent request rejected.')
        sequence = int(sequence_text)
        if str(sequence)!=sequence_text:
            raise AgentAuthenticationError('Agent request rejected.')
        identity,key = await run_in_threadpool(broker.registry.authenticate_message,
            request.headers['x-agent-id'],sequence,path,raw,request.headers['x-agent-signature'])
        fields = {'poll':(), 'check':('lease_id',), 'finish':('lease_id','failed'),
                  'result':('lease_id','case_id','status','duration_seconds','png_base64')}
        data = _object(raw,fields[operation])
        if operation=='poll':
            result = {'work':await run_in_threadpool(broker.claim,identity)}
        elif operation=='check':
            result = await run_in_threadpool(broker.check,identity,data['lease_id'])
        elif operation=='finish':
            result = await run_in_threadpool(broker.finish,identity,data['lease_id'],failed=data['failed'])
        else:
            encoded = data['png_base64']
            if encoded is not None and (not isinstance(encoded,str) or len(encoded)>350000):
                raise ValueError('Invalid evidence.')
            png = None if encoded is None else base64.b64decode(encoded,validate=True)
            result = await run_in_threadpool(broker.result,identity,data['lease_id'],data['case_id'],
                data['status'],data['duration_seconds'],png=png)
        body = json.dumps(result,allow_nan=False,separators=(',',':')).encode()
        if len(body)>MAX_MESSAGE:
            raise ValueError('Response exceeds the limit.')
        return Response(body,media_type='application/json',headers={
            'x-agent-response-signature':message_signature(key,path,sequence,body,response=True)})

    class Boundary:
        async def __call__(self,scope,receive,send):
            if scope['type']!='http':
                if scope['type']=='websocket':
                    await send({'type':'websocket.close','code':1008})
                else:
                    await app(scope,receive,send)
                return
            headers = scope.get('headers',[])
            def values(name): return [v for k,v in headers if k.lower()==name]
            async def secured(message):
                if message['type']=='http.response.start':
                    message['headers'] = list(message.get('headers',[]))+[
                        (b'cache-control',b'no-store'),(b'x-content-type-options',b'nosniff'),
                        (b'content-security-policy',b"default-src 'none'; frame-ancestors 'none'")]
                await send(message)
            async def deny(status):
                await JSONResponse({'detail':'Agent request rejected.'},status_code=status)(scope,receive,secured)
            if (scope['method']!='POST' or scope['path'] not in AGENT_PATHS or scope.get('query_string')
                    or scope.get('raw_path',scope['path'].encode())!=scope['path'].encode()):
                await deny(404); return
            security = (b'host',b'content-type',b'x-agent-id',b'x-agent-sequence',b'x-agent-signature')
            if (any(len(values(name))!=1 for name in security) or len(values(b'content-length'))>1
                    or values(b'host')!=[authority] or values(b'content-type')!=[b'application/json']
                    or any(values(name) for name in (b'origin',b'cookie',b'authorization',b'content-encoding'))
                    or any(k.lower().startswith(b'x-forwarded-') or k.lower()==b'forwarded' for k,_ in headers)):
                await deny(400); return
            body = bytearray()
            async def collect():
                while True:
                    message = await receive()
                    if message['type']!='http.request': raise ValueError()
                    chunk = message.get('body',b'')
                    if len(body)+len(chunk)>MAX_MESSAGE: raise OverflowError()
                    body.extend(chunk)
                    if not message.get('more_body',False): return
            try:
                await asyncio.wait_for(collect(),timeout=5)
            except OverflowError:
                await deny(413); return
            except (ValueError,TimeoutError):
                await deny(408); return
            delivered = False
            async def replay():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {'type':'http.request','body':bytes(body),'more_body':False}
                return await receive()
            await app(scope,replay,secured)
    return Boundary()


class AgentClient:
    """No listener, redirects, DNS names, proxies, browser cookies or auto-retries."""
    def __init__(self,origin,agent_id,token,*,sequence_start=1):
        self.port = validate_coordinator(origin)
        _id(agent_id)
        if not isinstance(token,SecretValue) or type(sequence_start) is not int or not 1<=sequence_start<=2147483647:
            raise ValueError('A private credential and bounded sequence are required.')
        self.agent_id,self.sequence = agent_id,sequence_start-1
        self._key = token_signing_key(token.value)

    def call(self,path,data):
        raw = json.dumps(data,allow_nan=False,separators=(',',':')).encode()
        self.sequence+=1
        signature = message_signature(self._key,path,self.sequence,raw)
        sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        connection = http.client.HTTPConnection('127.0.0.1',self.port,timeout=5)
        deadline = monotonic()+5
        def abort():
            try: sock.shutdown(socket.SHUT_RDWR)
            except OSError: pass
            sock.close()
        timer = Timer(5,abort)
        timer.daemon = True
        timer.start()
        try:
            sock.settimeout(5)
            sock.connect(('127.0.0.1',self.port))
            if sock.getpeername()[:2]!=('127.0.0.1',self.port): raise ValueError()
            connection.sock = sock
            connection.request('POST',path,body=raw,headers={'Content-Type':'application/json',
                'Connection':'close','X-Agent-Id':self.agent_id,'X-Agent-Sequence':str(self.sequence),
                'X-Agent-Signature':signature})
            response = connection.getresponse()
            if response.status!=200 or response.getheader('Content-Encoding','identity')!='identity':
                raise ValueError()
            if response.getheader('Content-Type','').split(';')[0]!='application/json': raise ValueError()
            signatures = [v for k,v in response.getheaders() if k.lower()=='x-agent-response-signature']
            if len(signatures)!=1 or not re.fullmatch(r'[0-9a-f]{64}',signatures[0]): raise ValueError()
            body = response.read(MAX_MESSAGE+1)
            if len(body)>MAX_MESSAGE or monotonic()>deadline: raise ValueError()
            expected = message_signature(self._key,path,self.sequence,body,response=True)
            if not hmac.compare_digest(expected,signatures[0]): raise ValueError()
            result = json.loads(body)
            if not isinstance(result,dict): raise ValueError()
            return result
        except (OSError,ValueError,http.client.HTTPException,UnicodeError):
            raise AgentTransportError('Agent coordinator exchange failed.') from None
        finally:
            timer.cancel()
            connection.close()
            sock.close()
