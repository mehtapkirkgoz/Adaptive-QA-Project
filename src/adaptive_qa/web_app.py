"""Loopback-only dashboard authentication; no test execution endpoints."""
from adaptive_qa.form_configuration import runtime_configuration

import asyncio
from collections import deque
import json
from pathlib import Path
from threading import Lock
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse, FileResponse, Response
from starlette.staticfiles import StaticFiles

from adaptive_qa.auth_store import AuthenticationError, AuthStore
from adaptive_qa.project_store import ProjectStore, ProjectNotFound
from adaptive_qa.dashboard_plan import review_project_plan, ConfigurationRequired
from adaptive_qa.dashboard_jobs import DashboardDiscoveryQueue, DiscoveryJobNotFound
from adaptive_qa.dashboard_worker import configuration_fingerprint
from adaptive_qa.dashboard_runs import DashboardRunQueue, TestRunNotFound
from adaptive_qa.dashboard_reports import build_run_report, compare_runs
from adaptive_qa.flaky_signals import build_flaky_report
from adaptive_qa.organization_store import OrganizationStore, OrganizationNotFound
from adaptive_qa.organization_projects import OrganizationProjects
from adaptive_qa.organization_admission import OrganizationCapacityExceeded
from adaptive_qa.organization_api import register_organization_routes


SESSION_COOKIE = 'adaptive_session'
CSRF_COOKIE = 'adaptive_csrf'


def _object(body, fields, *, optional=()):
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
    if not isinstance(data, dict) or (not set(fields) <= set(data) or not set(data) <= set(fields) | set(optional)):
        raise ValueError()
    return data


def create_app(store: AuthStore, *, port=8765, projects=None, ui_directory=None):
    """Trusted composition root. Bind the server to 127.0.0.1 only."""
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError('A local unprivileged port is required.')
    authority = f'127.0.0.1:{port}'
    origin = f'http://{authority}'
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    projects = projects if projects is not None else ProjectStore(store.database.with_name('projects.sqlite'))
    discovery = DashboardDiscoveryQueue(projects)
    runs = DashboardRunQueue(projects)
    organizations = OrganizationStore(projects)
    organization_projects = OrganizationProjects(organizations)
    attempts, lock = deque(), Lock()
    if ui_directory is not None:
        ui_root = Path(ui_directory).resolve(strict=True)
        if not (ui_root / 'index.html').is_file() or not (ui_root / 'assets').is_dir():
            raise ValueError('A built dashboard directory is required.')
        app.mount('/assets', StaticFiles(directory=ui_root / 'assets'), name='dashboard-assets')

        @app.get('/')
        def dashboard():
            return FileResponse(ui_root / 'index.html', media_type='text/html')

    @app.exception_handler(AuthenticationError)
    async def authentication_error(request, error):
        return JSONResponse({'detail': 'Authentication failed.'}, status_code=401)

    @app.exception_handler(ProjectNotFound)
    @app.exception_handler(DiscoveryJobNotFound)
    @app.exception_handler(TestRunNotFound)
    @app.exception_handler(OrganizationNotFound)
    async def missing_project(request, error):
        return JSONResponse({'detail': 'Project not found.'}, status_code=404)

    @app.exception_handler(OrganizationCapacityExceeded)
    async def organization_capacity(request, error):
        return JSONResponse({'detail': 'Organization capacity reached.'}, status_code=409)

    @app.get('/api/projects/{project_id}/runs')
    def list_runs(project_id: str, request: Request):
        return {'runs': runs.list(actor(request), project_id)}

    @app.get('/api/projects/{project_id}/flaky-signals')
    def flaky_signals(project_id: str, request: Request):
        return build_flaky_report(runs, actor(request), project_id)

    @app.post('/api/projects/{project_id}/runs', status_code=202)
    async def submit_run(project_id: str, request: Request):
        owner = await run_in_threadpool(actor, request, mutation=True)
        data = _object(await request.body(), ('discovery_job_id', 'case_ids'))
        if not isinstance(data['case_ids'], list):
            raise ValueError()
        return await run_in_threadpool(runs.submit, owner, project_id,
                                       data['discovery_job_id'], tuple(data['case_ids']))

    @app.get('/api/projects/{project_id}/runs/{run_id}')
    def get_run(project_id: str, run_id: str, request: Request):
        return runs.get(actor(request), project_id, run_id)

    @app.post('/api/projects/{project_id}/runs/{run_id}/rerun', status_code=202)
    async def rerun(project_id: str, run_id: str, request: Request):
        owner = await run_in_threadpool(actor, request, mutation=True)
        data = _object(await request.body(), ('discovery_job_id', 'case_ids'))
        if not isinstance(data['case_ids'], list):
            raise ValueError()
        return await run_in_threadpool(runs.submit, owner, project_id, data['discovery_job_id'],
                                       tuple(data['case_ids']), rerun_of=run_id)

    @app.get('/api/projects/{project_id}/runs/{run_id}/compare/{baseline_id}')
    def comparison(project_id: str, run_id: str, baseline_id: str, request: Request):
        return compare_runs(runs, actor(request), project_id, baseline_id, run_id)

    @app.get('/api/projects/{project_id}/runs/{run_id}/report')
    def run_report(project_id: str, run_id: str, request: Request):
        return build_run_report(runs, actor(request), project_id, run_id)

    @app.get('/api/projects/{project_id}/runs/{run_id}/report/status/{status}')
    def filtered_run_report(project_id: str, run_id: str, status: str, request: Request):
        return build_run_report(runs, actor(request), project_id, run_id, status=status)

    @app.get('/api/projects/{project_id}/runs/{run_id}/report/download')
    def download_run_report(project_id: str, run_id: str, request: Request):
        report = build_run_report(runs, actor(request), project_id, run_id)
        return JSONResponse(report, headers={
            'Content-Disposition': 'attachment; filename="test-run-report.json"'})

    @app.post('/api/projects/{project_id}/runs/{run_id}/cancel')
    async def cancel_run(project_id: str, run_id: str, request: Request):
        owner = await run_in_threadpool(actor, request, mutation=True)
        _object(await request.body(), ())
        return await run_in_threadpool(runs.cancel, owner, project_id, run_id)

    @app.get('/api/projects/{project_id}/runs/{run_id}/evidence/{evidence_id}')
    def run_evidence(project_id: str, run_id: str, evidence_id: str, request: Request):
        data = runs.evidence(actor(request), project_id, run_id, evidence_id)
        return Response(data, media_type='image/png', headers={
            'Content-Disposition': 'inline; filename="test-evidence.png"'})

    @app.get('/api/projects/{project_id}/discovery')
    def list_discovery(project_id: str, request: Request):
        return {'jobs': discovery.list(actor(request), project_id)}

    @app.post('/api/projects/{project_id}/discovery', status_code=202)
    async def submit_discovery(project_id: str, request: Request):
        owner = await run_in_threadpool(actor, request, mutation=True)
        _object(await request.body(), ())
        return await run_in_threadpool(discovery.submit, owner, project_id)

    @app.get('/api/projects/{project_id}/discovery/{job_id}')
    def get_discovery(project_id: str, job_id: str, request: Request):
        owner = actor(request)
        job = discovery.get(owner, project_id, job_id)
        if 'report' in job:
            saved = projects.configuration(owner, project_id)
            snapshot = runtime_configuration(saved) if saved['configured'] else {}
            job['configuration_current'] = configuration_fingerprint(snapshot) == job['report'].get('configuration_fingerprint')
        return job

    @app.post('/api/projects/{project_id}/discovery/{job_id}/cancel')
    async def cancel_discovery(project_id: str, job_id: str, request: Request):
        owner = await run_in_threadpool(actor, request, mutation=True)
        _object(await request.body(), ())
        return await run_in_threadpool(discovery.cancel, owner, project_id, job_id)

    @app.exception_handler(ConfigurationRequired)
    async def configuration_required(request, error):
        return JSONResponse({'detail': 'Save project configuration before reviewing a plan.'}, status_code=409)

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

    if not (getattr(store, 'local_free', False) or getattr(store, 'local_licensed', False)):
        register_organization_routes(app, organizations, organization_projects, actor, _object, store)

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

    @app.get('/api/projects/{project_id}/plan')
    def review_plan(project_id: str, request: Request):
        return review_project_plan(projects, actor(request), project_id)

    @app.post('/api/projects/{project_id}/interactive/review')
    async def review_interactive_fixture(project_id: str, request: Request):
        from adaptive_qa.form_configuration import decode_form_mappings
        from adaptive_qa.interactive_review import review_saved_interactive
        owner = await run_in_threadpool(actor, request, mutation=True)
        data = _object(await request.body(), ('fixture_id', 'completion'), optional=('timeout_seconds',))
        if not isinstance(data['fixture_id'],str): raise ValueError()
        completion = decode_form_mappings({'project_id': project_id, 'mappings': [data['completion']]}).mappings[0]
        review = await run_in_threadpool(review_saved_interactive, projects, owner, project_id,
            fixture_id=data['fixture_id'], completion=completion, timeout_seconds=data.get('timeout_seconds', 15))
        return review.public()

    if getattr(store, 'local_free', False) or getattr(store, 'local_licensed', False):
        from adaptive_qa.interactive_queue import OwnedInteractiveQueue
        interactive = OwnedInteractiveQueue(projects)
        from adaptive_qa.api_queue import LocalApiQueue
        local_api = LocalApiQueue(projects)

        @app.post('/api/projects/{project_id}/local-api/jobs', status_code=202)
        async def submit_saved_local_api(project_id: str, request: Request):
            owner = await run_in_threadpool(actor, request, mutation=True)
            data = _object(await request.body(), ('confirmed_contract_fingerprint',))
            return await run_in_threadpool(local_api.submit, owner, project_id, data['confirmed_contract_fingerprint'])

        @app.get('/api/projects/{project_id}/local-api/jobs')
        def list_saved_local_api(project_id: str, request: Request):
            return {'jobs': local_api.list(actor(request), project_id)}

        @app.get('/api/projects/{project_id}/local-api/jobs/{job_id}')
        def get_saved_local_api(project_id: str, job_id: str, request: Request):
            return local_api.get(actor(request), project_id, job_id)

        @app.post('/api/projects/{project_id}/local-api/jobs/{job_id}/cancel')
        async def cancel_saved_local_api(project_id: str, job_id: str, request: Request):
            owner = await run_in_threadpool(actor, request, mutation=True)
            _object(await request.body(), ())
            return await run_in_threadpool(local_api.cancel, owner, project_id, job_id)

        @app.post('/api/projects/{project_id}/local-api/review')
        async def review_saved_local_api(project_id: str, request: Request):
            from adaptive_qa.saved_api_review import review_saved_api
            owner = await run_in_threadpool(actor, request, mutation=True)
            _object(await request.body(), ())
            return await run_in_threadpool(review_saved_api, projects, owner, project_id)

        @app.post('/api/projects/{project_id}/interactive/jobs', status_code=202)
        async def submit_interactive_fixture(project_id: str, request: Request):
            import hmac
            import re
            from adaptive_qa.form_configuration import decode_form_mappings
            from adaptive_qa.interactive_review import review_saved_interactive
            owner = await run_in_threadpool(actor, request, mutation=True)
            data = _object(await request.body(), ('fixture_id', 'completion', 'confirmed_contract_fingerprint'), optional=('timeout_seconds',))
            if not isinstance(data['fixture_id'],str): raise ValueError()
            digest = data['confirmed_contract_fingerprint']
            if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
                raise ValueError()
            completion = decode_form_mappings({'project_id': project_id, 'mappings': [data['completion']]}).mappings[0]
            review = await run_in_threadpool(review_saved_interactive, projects, owner, project_id,
                fixture_id=data['fixture_id'], completion=completion, timeout_seconds=data.get('timeout_seconds', 15))
            if not hmac.compare_digest(digest, review.submission.fingerprint()):
                raise ValueError()
            return await run_in_threadpool(interactive.submit, owner, review)

        @app.post('/api/projects/{project_id}/interactive/local/review')
        async def review_reusable_local_form(project_id: str, request: Request):
            from adaptive_qa.form_configuration import decode_form_mappings
            from adaptive_qa.interactive_review import review_saved_local_form
            owner = await run_in_threadpool(actor, request, mutation=True)
            data = _object(await request.body(), ('completion',), optional=('timeout_seconds',))
            completion = decode_form_mappings({'project_id': project_id, 'mappings': [data['completion']]}).mappings[0]
            review = await run_in_threadpool(review_saved_local_form, projects, owner, project_id,
                completion=completion, timeout_seconds=data.get('timeout_seconds', 15))
            return review.public()

        @app.post('/api/projects/{project_id}/interactive/local/jobs', status_code=202)
        async def submit_reusable_local_form(project_id: str, request: Request):
            import hmac
            import re
            from adaptive_qa.form_configuration import decode_form_mappings
            from adaptive_qa.interactive_review import review_saved_local_form
            owner = await run_in_threadpool(actor, request, mutation=True)
            data = _object(await request.body(), ('completion', 'confirmed_contract_fingerprint'), optional=('timeout_seconds',))
            digest = data['confirmed_contract_fingerprint']
            if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest): raise ValueError()
            completion = decode_form_mappings({'project_id': project_id, 'mappings': [data['completion']]}).mappings[0]
            review = await run_in_threadpool(review_saved_local_form, projects, owner, project_id,
                completion=completion, timeout_seconds=data.get('timeout_seconds', 15))
            if not hmac.compare_digest(digest, review.submission.fingerprint()): raise ValueError()
            return await run_in_threadpool(interactive.submit, owner, review)

        @app.get('/api/projects/{project_id}/interactive/jobs')
        def list_interactive_jobs(project_id: str, request: Request):
            return {'jobs': interactive.list(actor(request), project_id)}

        @app.get('/api/projects/{project_id}/interactive/jobs/{job_id}')
        def get_interactive_job(project_id: str, job_id: str, request: Request):
            return interactive.get(actor(request), project_id, job_id)

        @app.post('/api/projects/{project_id}/interactive/jobs/{job_id}/cancel')
        async def cancel_interactive_job(project_id: str, job_id: str, request: Request):
            owner = await run_in_threadpool(actor, request, mutation=True)
            _object(await request.body(), ())
            return await run_in_threadpool(interactive.cancel, owner, project_id, job_id)

    @app.put('/api/projects/{project_id}/configuration')
    async def put_configuration(project_id: str, request: Request):
        owner = await run_in_threadpool(actor, request, mutation=True)
        data = _object(await request.body(), ('base_url', 'allowed_hosts',
                                            'allow_data_changes', 'secret_references'), optional=('form_mappings','local_form_binding','local_api_binding'))
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

    if getattr(store, 'local_licensed', False):
        def license_status():
            from adaptive_qa.licensing import LicenseError
            try:
                claims = projects.licenses.current()
            except LicenseError:
                return {'status': 'invalid_or_expired', 'execution_allowed': False}
            return {'status': 'valid' if claims else 'absent', 'execution_allowed': claims is not None,
                    'max_projects': claims.max_projects if claims else 0,
                    'max_concurrent_runs': claims.max_concurrent_runs if claims else 0,
                    'expires_at': claims.expires_at if claims else None}

        @app.get('/api/local/license')
        def local_license(request: Request):
            actor(request)
            return license_status()

        @app.post('/api/local/license')
        async def install_local_license(request: Request):
            await run_in_threadpool(actor, request, mutation=True)
            data = _object(await request.body(), ('document',))
            if not isinstance(data['document'], str) or len(data['document']) > 8192:
                raise ValueError()
            await run_in_threadpool(projects.licenses.install, data['document'].encode('utf-8'))
            return await run_in_threadpool(license_status)

    @app.get('/api/auth/me')
    def me(request: Request):
        if getattr(store, 'local_free', False):
            if (request.headers.get('sec-fetch-site') == 'cross-site'
                    or request.headers.get('origin') not in (None, origin)):
                return JSONResponse({'detail': 'Request rejected.'}, status_code=403)
            grant = store.bootstrap(request.cookies.get(SESSION_COOKIE))
            response = JSONResponse({'user_id': grant.actor.user_id, 'edition': 'free',
                                     'account_required': False, 'max_projects': 1, 'test_data_location': 'local'})
            for name, value, hidden in ((SESSION_COOKIE, grant.token.value, True),
                                        (CSRF_COOKIE, grant.csrf_token.value, False)):
                response.set_cookie(name, value, max_age=store.session_seconds,
                                    httponly=hidden, samesite='strict', secure=False, path='/')
            return response
        try:
            actor = store.actor_for_session(request.cookies.get(SESSION_COOKIE))
        except AuthenticationError:
            return JSONResponse({'detail': 'Authentication failed.'}, status_code=401)
        return JSONResponse({'user_id': actor.user_id, **({'edition': 'professional'} if getattr(store, 'local_licensed', False) else {})})

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
                        (b'content-security-policy', b"default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"),
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
            delivered = False
            async def replay():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
                return await receive()
            await app(scope, replay, secured_send)

    return Boundary()
