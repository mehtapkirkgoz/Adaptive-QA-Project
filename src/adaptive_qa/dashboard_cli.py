"""Trusted local dashboard provisioning and single-process loopback serving."""

import getpass
from pathlib import Path
import sqlite3
import sys
import warnings

from adaptive_qa.auth_store import AuthenticationError, AuthStore
from adaptive_qa.web_app import create_app


def configure_parser(subparsers):
    parser = subparsers.add_parser('dashboard', help='Manage the local dashboard')
    commands = parser.add_subparsers(dest='dashboard_command', required=True)
    for name in ('create-user', 'serve', 'discovery-once', 'recover-discovery', 'recover-organization-discovery', 'run-once', 'recover-runs', 'prune-evidence'):
        command = commands.add_parser(name)
        command.add_argument('--database', type=Path, default=Path('artifacts/dashboard/projects.sqlite'
            if name in ('discovery-once', 'recover-discovery', 'recover-organization-discovery', 'run-once', 'recover-runs', 'prune-evidence') else 'artifacts/dashboard/auth.sqlite'))
        if name == 'prune-evidence':
            command.add_argument('--limit', type=int, default=100)
        if name == 'serve':
            command.add_argument('--port', type=int, default=8765)
            command.add_argument('--ui-directory', type=Path, default=Path('frontend/dist'))


def run(args):
    if args.dashboard_command == 'recover-organization-discovery':
        from adaptive_qa.project_store import ProjectStore
        from adaptive_qa.organization_store import OrganizationStore
        from adaptive_qa.organization_projects import OrganizationProjects
        from adaptive_qa.organization_discovery import OrganizationDiscoveryQueue
        queue = OrganizationDiscoveryQueue(OrganizationProjects(OrganizationStore(ProjectStore(args.database))))
        print(queue.recover_interrupted())
        return
    if args.dashboard_command == 'prune-evidence':
        from adaptive_qa.dashboard_runs import DashboardRunQueue
        from adaptive_qa.project_store import ProjectStore
        print(DashboardRunQueue(ProjectStore(args.database)).prune_expired_evidence(limit=args.limit))
        return
    if args.dashboard_command in ('run-once', 'recover-runs'):
        from adaptive_qa.dashboard_runs import DashboardRunQueue
        from adaptive_qa.dashboard_run_worker import process_run_once
        from adaptive_qa.project_store import ProjectStore
        queue = DashboardRunQueue(ProjectStore(args.database))
        print(queue.recover_interrupted() if args.dashboard_command == 'recover-runs'
              else (process_run_once(queue) or 'No queued test runs.'))
        return
    if args.dashboard_command in ('discovery-once', 'recover-discovery'):
        from adaptive_qa.dashboard_jobs import DashboardDiscoveryQueue
        from adaptive_qa.project_store import ProjectStore
        from adaptive_qa.dashboard_worker import process_discovery_once
        queue = DashboardDiscoveryQueue(ProjectStore(args.database))
        if args.dashboard_command == 'recover-discovery':
            print(queue.recover_interrupted())
        else:
            outcome = process_discovery_once(queue)
            if outcome is None:
                from adaptive_qa.organization_discovery import OrganizationDiscoveryQueue
                from adaptive_qa.organization_projects import OrganizationProjects
                from adaptive_qa.organization_store import OrganizationStore
                outcome = process_discovery_once(OrganizationDiscoveryQueue(OrganizationProjects(OrganizationStore(queue.projects))))
            print(outcome or 'No queued discovery work.')
        return
    if args.dashboard_command == 'create-user':
        # Fail closed instead of getpass falling back to echoed stdin.
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise ValueError('Account provisioning requires an interactive terminal.')
        email = input('Email: ')
        with warnings.catch_warnings():
            warnings.simplefilter('error', getpass.GetPassWarning)
            try:
                password = getpass.getpass('Password (12+ characters): ')
                confirmation = getpass.getpass('Confirm password: ')
            except getpass.GetPassWarning:
                raise ValueError('Hidden password input is unavailable in this terminal.') from None
        if password != confirmation:
            raise ValueError('Passwords do not match.')
        try:
            AuthStore(args.database).create_user(email, password)
        except (ValueError, AuthenticationError, sqlite3.Error):
            raise ValueError('Account provisioning failed. Use a unique valid email and a password of 12+ characters, at most 256 UTF-8 bytes.') from None
        print('Local account created. No credentials were printed or saved in plaintext.')
        return
    if type(args.port) is not int or not 1024 <= args.port <= 65535:
        raise ValueError('Port must be an integer in [1024, 65535].')
    import uvicorn
    ui_directory = getattr(args, 'ui_directory', Path('frontend/dist'))
    app = create_app(AuthStore(args.database), port=args.port,
                     ui_directory=ui_directory if ui_directory.is_dir() else None)
    print(f'Local authentication API: http://127.0.0.1:{args.port}/api/auth/me')
    if ui_directory.is_dir():
        print(f'Dashboard: http://127.0.0.1:{args.port}/')
    else:
        print('Dashboard build is missing. Run npm ci and npm run build in frontend/.')
    print('Press Ctrl+C to stop.')
    uvicorn.run(app, host='127.0.0.1', port=args.port, workers=1,
                proxy_headers=False, access_log=False, log_level='warning',
                limit_concurrency=32, timeout_keep_alive=5)
