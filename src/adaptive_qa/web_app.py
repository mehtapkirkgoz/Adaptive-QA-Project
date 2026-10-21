"""Loopback-only dashboard authentication; no test execution endpoints."""

import asyncio
from collections import deque
import json
from threading import Lock
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from adaptive_qa.auth_store import AuthenticationError, AuthStore
from adaptive_qa.project_store import ProjectStore, ProjectNotFound


SESSION_COOKIE = 'adaptive_session'
CSRF_COOKIE = 'adaptive_csrf'


def _object(body, fields):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError()
            result[key] = value
        return result
    def invalid_constant(value):
        raise ValueError()
    try:
        data = json.loads(body.decode('utf-8'), object_pairs_hook=unique,
                          parse_constant=invalid_constant)
    except (UnicodeError, RecursionError):
        raise ValueError() from None
    if not isinstance(data, dict) or set(data) != set(fields):
        raise ValueError()
    return data


def create_app(store: AuthStore, *, port=8765, projects=None):
    """Trusted composition root. Bind the server to 127.0.0.1 only."""
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError('A local unprivileged port is required.')
    authority = f'127.0.0.1:{port}'
    origin = f'http://{authority}'
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    projects = projects if projects is not None else ProjectStore(store.database.with_name('projects.sqlite'))
    attempts, lock = deque(), Lock()

    @app.exception_handler(AuthenticationError)
    async def authentication_error(request, error):
        return JSONResponse({'detail': 'Authentication failed.'}, status_code=401)

    @app.exception_handler(ProjectNotFound)
    async def missing_project(request, error):
        return JSONResponse({'detail': 'Project not found.'}, status_code=404)

    @app.exception_handler(ValueError)
    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        return JSONResponse({'detail': 'Invalid request.'}, status_code=400)

    def actor(request, *, mutation=False):
        token = request.cookies.get(SESSION_COOKIE)
        if mutation:
            return store.verify_csrf(token, request.headers.get('x-csrf-token'))
        return store.actor_for_session(token)

    def public_project(project):
        return {'project_id': project.project_id, 'name': project.name}

    @app.get('/api/projects')
    def list_projects(request: Request):
        owner = actor(request)
        pairs = list(request.query_params.multi_items())
        if len({key for key, _ in pairs}) != len(pairs) or any(key not in ('limit', 'offset') for key, _ in pairs):
            raise ValueError()
        def number(name, default):
            value = request.query_params.get(name, str(default))
            if not value.isascii() or not value.isdecimal() or len(value) > 6:
                raise ValueError()
            return int(value)
        limit, offset = number('limit', 20), number('offset', 0)
        return {'projects': [public_project(p) for p in projects.list(owner, limit=limit, offset=offset)],
                'limit': limit, 'offset': offset}

    @app.post('/api/projects', status_code=201)
    async def create_project(request: Request):
        owner = await run_in_threadpool(actor, request, mutation=True)
        data = _object(await request.body(), ('name',))
        project = await run_in_threadpool(projects.create, owner, data['name'])
        return public_project(project)

    @app.get('/api/projects/{project_id}')
    def get_project(project_id: str, request: Request):
        return public_project(projects.get(actor(request), project_id))

    @app.get('/api/projects/{project_id}/configuration')
    def get_configuration(project_id: str, request: Request):
        return projects.configuration(actor(request), project_id)

    @app.put('/api/projects/{project_id}/configuration')
    async def put_configuration(project_id: str, request: Request):
        owner = await run_in_threadpool(actor, request, mutation=True)
        data = _object(await request.body(), ('base_url', 'allowed_hosts',
                                            'allow_data_changes', 'secret_references'))
        return await run_in_threadpool(projects.save_configuration, owner, project_id, data)

    @app.patch('/api/projects/{project_id}')
    async def rename_project(project_id: str, request: Request):
        owner = await run_in_threadpool(actor, request, mutation=True)
        data = _object(await request.body(), ('name',))
        project = await run_in_threadpool(projects.rename, owner, project_id, data['name'])
        return public_project(project)

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
            data = _object(await request.body(), ('email', 'password'))
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
            if (any(len(values(name)) > 1 for name in
                    (b'cookie', b'x-csrf-token', b'content-length', b'content-type', b'origin'))
                    or values(b'content-encoding')):
                await deny(400)
                return
            # Duplicate credential cookie names are ambiguous even in a single header.
            cookie_names = [part.strip().split(b'=', 1)[0] for value in values(b'cookie')
                            for part in value.split(b';')]
            if any(cookie_names.count(name.encode()) > 1 for name in (SESSION_COOKIE, CSRF_COOKIE)):
                await deny(400)
                return
            query = scope.get('query_string', b'')
            allowed_query = scope['method'] == 'GET' and scope['path'] == '/api/projects' and len(query) <= 128
            if (values(b'host') != [authority.encode()] or (query and not allowed_query)
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
                    chunk = message.get('body', b'')
                    if len(body) + len(chunk) > 2048:
                        raise OverflowError()
                    body.extend(chunk)
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
