"""Authenticated local organization/project routes; no execution admission yet."""

from dataclasses import asdict
from fastapi import Request
from starlette.concurrency import run_in_threadpool
from adaptive_qa.organization_discovery import OrganizationDiscoveryQueue


def register_organization_routes(app, organizations, projects, actor, parse_object):
    discovery = OrganizationDiscoveryQueue(projects)

    @app.get('/api/organizations/{organization_id}/projects/{project_id}/discovery')
    def list_discovery(organization_id: str, project_id: str, request: Request):
        return {'jobs': discovery.list(actor(request), organization_id, project_id)}

    @app.post('/api/organizations/{organization_id}/projects/{project_id}/discovery', status_code=202)
    async def submit_discovery(organization_id: str, project_id: str, request: Request):
        identity = await run_in_threadpool(actor, request, mutation=True)
        parse_object(await request.body(), ())
        return await run_in_threadpool(discovery.submit, identity, organization_id, project_id)

    @app.get('/api/organizations/{organization_id}/projects/{project_id}/discovery/{job_id}')
    def get_discovery(organization_id: str, project_id: str, job_id: str, request: Request):
        return discovery.get(actor(request), organization_id, project_id, job_id)

    @app.post('/api/organizations/{organization_id}/projects/{project_id}/discovery/{job_id}/cancel')
    async def cancel_discovery(organization_id: str, project_id: str, job_id: str, request: Request):
        identity = await run_in_threadpool(actor, request, mutation=True)
        parse_object(await request.body(), ())
        return await run_in_threadpool(discovery.cancel, identity, organization_id, project_id, job_id)
    @app.get('/api/organizations')
    def list_organizations(request: Request):
        return {'organizations': organizations.list(actor(request))}

    @app.post('/api/organizations', status_code=201)
    async def create_organization(request: Request):
        identity = await run_in_threadpool(actor, request, mutation=True)
        data = parse_object(await request.body(), ('name',))
        organization_id = await run_in_threadpool(organizations.create, identity, data['name'])
        return {'organization_id': organization_id, 'name': data['name'], 'role': 'owner'}

    @app.get('/api/organizations/{organization_id}')
    def get_organization(organization_id: str, request: Request):
        identity = actor(request)
        membership = organizations.membership(identity, organization_id)
        return {'organization_id': organization_id, 'role': membership.role.value,
                'quota': asdict(organizations.quota(identity, organization_id))}

    @app.get('/api/organizations/{organization_id}/projects')
    def list_projects(organization_id: str, request: Request):
        return {'projects': projects.list(actor(request), organization_id)}

    @app.post('/api/organizations/{organization_id}/projects', status_code=201)
    async def create_project(organization_id: str, request: Request):
        identity = await run_in_threadpool(actor, request, mutation=True)
        data = parse_object(await request.body(), ('name',))
        return await run_in_threadpool(projects.create, identity, organization_id, data['name'])

    @app.get('/api/organizations/{organization_id}/projects/{project_id}')
    def get_project(organization_id: str, project_id: str, request: Request):
        return projects.get(actor(request), organization_id, project_id)

    @app.patch('/api/organizations/{organization_id}/projects/{project_id}')
    async def rename_project(organization_id: str, project_id: str, request: Request):
        identity = await run_in_threadpool(actor, request, mutation=True)
        data = parse_object(await request.body(), ('name',))
        return await run_in_threadpool(projects.rename, identity, organization_id, project_id, data['name'])

    @app.get('/api/organizations/{organization_id}/projects/{project_id}/configuration')
    def configuration(organization_id: str, project_id: str, request: Request):
        return projects.configuration(actor(request), organization_id, project_id)

    @app.put('/api/organizations/{organization_id}/projects/{project_id}/configuration')
    async def save_configuration(organization_id: str, project_id: str, request: Request):
        identity = await run_in_threadpool(actor, request, mutation=True)
        data = parse_object(await request.body(), ('base_url', 'allowed_hosts',
                                                 'allow_data_changes', 'secret_references'))
        return await run_in_threadpool(projects.save_configuration, identity, organization_id, project_id, data)
