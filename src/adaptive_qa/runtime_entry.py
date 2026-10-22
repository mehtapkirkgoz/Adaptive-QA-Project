"""Stable local launcher; application imports come from the selected wheel."""

import argparse
import importlib.util
from pathlib import Path
from urllib.parse import urlsplit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--origin', required=True)
    parser.add_argument('--role', required=True)
    parser.add_argument('--selection', required=True)
    args = parser.parse_args()
    # Load the current trusted supervisor independently of the selected app's
    # version; older application wheels need not contain this launcher module.
    specification = importlib.util.spec_from_file_location('adaptive_local_supervisor', Path(__file__).with_name('local_runtime.py'))
    supervisor = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(supervisor)
    from adaptive_qa.deployment import DeploymentPlan, Environment
    from adaptive_qa.auth_store import AuthStore
    from adaptive_qa.project_store import ProjectStore
    from adaptive_qa.dashboard_runs import DashboardRunQueue
    plan = DeploymentPlan(Environment.LOCAL, args.data_root, args.origin)
    with supervisor.component_lease(plan, args.role, args.selection) as (selected, release, data):
        import adaptive_qa
        if not Path(adaptive_qa.__file__).resolve().is_relative_to(release / 'site'):
            raise ValueError('Application imports did not resolve to the selected wheel.')
        projects = ProjectStore(data / 'projects.sqlite')
        if args.role == 'serve':
            import uvicorn
            from adaptive_qa.web_app import create_app
            port = urlsplit(plan.public_origin).port
            application = create_app(AuthStore(data / 'auth.sqlite'), projects=projects,
                                     port=port, ui_directory=release / 'ui')
            async def identified(scope, receive, send):
                async def marked(message):
                    if message['type'] == 'http.response.start':
                        message['headers'] = list(message.get('headers', [])) + [
                            (b'x-adaptive-qa-release', selected['release_id'].encode('ascii'))]
                    await send(message)
                await application(scope, receive, marked)
            uvicorn.run(identified, host='127.0.0.1', port=port, workers=1,
                        proxy_headers=False, access_log=False, log_level='critical',
                        limit_concurrency=32, timeout_keep_alive=5)
        elif args.role == 'run-once':
            from adaptive_qa.dashboard_run_worker import process_run_once
            outcome = process_run_once(DashboardRunQueue(projects))
            if outcome is None and importlib.util.find_spec('adaptive_qa.organization_runs') is not None:
                from adaptive_qa.organization_runs import OrganizationRunQueue
                from adaptive_qa.organization_discovery import OrganizationDiscoveryQueue
                from adaptive_qa.organization_projects import OrganizationProjects
                from adaptive_qa.organization_store import OrganizationStore
                outcome = process_run_once(OrganizationRunQueue(OrganizationDiscoveryQueue(OrganizationProjects(OrganizationStore(projects)))))
            if outcome is not None and outcome.get('status') == 'error':
                raise SystemExit(2)
        elif args.role == 'discovery-once':
            from adaptive_qa.dashboard_jobs import DashboardDiscoveryQueue
            from adaptive_qa.dashboard_worker import process_discovery_once
            outcome = process_discovery_once(DashboardDiscoveryQueue(projects))
            if outcome is None and importlib.util.find_spec('adaptive_qa.organization_discovery') is not None:
                from adaptive_qa.organization_discovery import OrganizationDiscoveryQueue
                from adaptive_qa.organization_projects import OrganizationProjects
                from adaptive_qa.organization_store import OrganizationStore
                outcome = process_discovery_once(OrganizationDiscoveryQueue(OrganizationProjects(OrganizationStore(projects))))
            if outcome is not None and outcome.get('status') == 'error':
                raise SystemExit(2)
        else:
            raise ValueError('Unknown runtime role.')


if __name__ == '__main__':
    main()
