"""Loopback-only dashboard authentication; no test execution endpoints."""

import asyncio
from collections import deque
import json
from threading import Lock
import time

from fastapi import FastAPI, Request
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from adaptive_qa.auth_store import AuthenticationError, AuthStore


SESSION_COOKIE = 'adaptive_session'
CSRF_COOKIE = 'adaptive_csrf'


def create_app(store: AuthStore, *, port=8765):
    """Trusted composition root. Bind the server to 127.0.0.1 only."""
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError('A local unprivileged port is required.')
    authority = f'127.0.0.1:{port}'
    origin = f'http://{authority}'
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    attempts, lock = deque(), Lock()

    @app.post('/api/auth/login')
    async def login(request: Request):
        with lock:
            now = time.monotonic()
            while attempts and attempts[0] <= now - 60:
                attempts.popleft()
            if len(attempts) >= 20:
                return JSONResponse({'detail': 'Authentication failed.'}, status_code=401)
            attempts.append(now)
        try:
            def unique(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError()
                    result[key] = value
                return result
            data = json.loads((await request.body()).decode('utf-8'), object_pairs_hook=unique)
            if not isinstance(data, dict) or set(data) != {'email', 'password'}:
                raise ValueError()
            grant = await run_in_threadpool(store.login, data['email'], data['password'])
        except (ValueError, UnicodeError, AuthenticationError):
            return JSONResponse({'detail': 'Authentication failed.'}, status_code=401)
        response = JSONResponse({'user_id': grant.actor.user_id})
        for name, value, hidden in ((SESSION_COOKIE, grant.token.value, True),
                                    (CSRF_COOKIE, grant.csrf_token.value, False)):
            response.set_cookie(name, value, max_age=store.session_seconds,
                                httponly=hidden, samesite='strict', secure=False, path='/')
        return response

    @app.get('/api/auth/me')
    def me(request: Request):
        try:
            actor = store.actor_for_session(request.cookies.get(SESSION_COOKIE))
        except AuthenticationError:
            return JSONResponse({'detail': 'Authentication failed.'}, status_code=401)
        return JSONResponse({'user_id': actor.user_id})

    @app.post('/api/auth/logout')
    def logout(request: Request):
        try:
            token = request.cookies.get(SESSION_COOKIE)
            store.verify_csrf(token, request.headers.get('x-csrf-token'))
            store.logout(token)
        except AuthenticationError:
            return JSONResponse({'detail': 'Authentication failed.'}, status_code=401)
        response = JSONResponse({'logged_out': True})
        for name in (SESSION_COOKIE, CSRF_COOKIE):
            response.delete_cookie(name, path='/', samesite='strict',
                                   httponly=name == SESSION_COOKIE)
        return response

    class Boundary:
        async def __call__(self, scope, receive, send):
            if scope['type'] != 'http':
                if scope['type'] == 'websocket':
                    await send({'type': 'websocket.close', 'code': 1008})
                    return
                await app(scope, receive, send)
                return
            headers = scope.get('headers', [])
            def values(name):
                return [v for k, v in headers if k.lower() == name]
            async def secured_send(message):
                if message['type'] == 'http.response.start':
                    message['headers'] = list(message.get('headers', [])) + [
                        (b'cache-control', b'no-store'),
                        (b'x-content-type-options', b'nosniff'),
                        (b'content-security-policy', b"default-src 'none'; connect-src 'self'; frame-ancestors 'none'"),
                        (b'referrer-policy', b'no-referrer')]
                await send(message)
            async def deny(status):
                await JSONResponse({'detail': 'Request rejected.'}, status_code=status)(scope, receive, secured_send)
            if (values(b'host') != [authority.encode()] or scope.get('query_string')
                    or any(k.lower().startswith(b'x-forwarded-') or k.lower() == b'forwarded' for k, _ in headers)):
                await deny(400)
                return
            if scope['method'] not in ('GET', 'HEAD'):
                if values(b'origin') != [origin.encode()]:
                    await deny(403)
                    return
                if values(b'content-type') != [b'application/json']:
                    await deny(415)
                    return
            # Actual received bytes are bounded even when Content-Length is absent or false.
            body = bytearray()
            async def collect():
                while True:
                    message = await receive()
                    if message['type'] != 'http.request':
                        raise ValueError()
                    body.extend(message.get('body', b''))
                    if len(body) > 2048:
                        raise OverflowError()
                    if not message.get('more_body', False):
                        return
            try:
                await asyncio.wait_for(collect(), timeout=5)
            except OverflowError:
                await deny(413)
                return
            except (ValueError, TimeoutError):
                await deny(408)
                return
            async def replay():
                return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
            await app(scope, replay, secured_send)

    return Boundary()
