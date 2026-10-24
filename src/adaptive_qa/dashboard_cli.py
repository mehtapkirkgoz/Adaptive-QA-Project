"""Trusted local dashboard provisioning and single-process loopback serving."""

import getpass
import json
from pathlib import Path
import sqlite3
import sys
import warnings

from adaptive_qa.auth_store import AuthenticationError, AuthStore
from adaptive_qa.web_app import create_app


def configure_parser(subparsers):
    parser = subparsers.add_parser('dashboard', help='Manage the local dashboard')
    commands = parser.add_subparsers(dest='dashboard_command', required=True)
    for name in ('create-user', 'serve', 'free-serve', 'free-worker-cycle', 'free-interactive-once', 'free-recover-interactive', 'discovery-once', 'recover-discovery', 'recover-organization-discovery', 'run-once', 'recover-runs', 'recover-organization-runs', 'prune-evidence', 'maintenance-once'):
        command = commands.add_parser(name)
        command.add_argument('--database', type=Path, default=Path('artifacts/dashboard/projects.sqlite'
            if name in ('discovery-once', 'recover-discovery', 'recover-organization-discovery', 'run-once', 'recover-runs', 'recover-organization-runs', 'prune-evidence', 'maintenance-once') else 'artifacts/dashboard/auth.sqlite'))
        if name in ('prune-evidence', 'maintenance-once'):
            command.add_argument('--limit', type=int, default=100)
        if name in ('free-serve', 'free-worker-cycle', 'free-interactive-once', 'free-recover-interactive'):
            command.set_defaults(database=Path('artifacts/local-free/projects.sqlite'))
        if name in ('serve', 'free-serve'):
            command.add_argument('--port', type=int, default=8766 if name == 'free-serve' else 8765)
            command.add_argument('--ui-directory', type=Path, default=Path('frontend/dist'))


def run(args):
    if args.dashboard_command in ('free-worker-cycle', 'free-interactive-once', 'free-recover-interactive'):
        from adaptive_qa.local_free import LocalFreeProjects
        from adaptive_qa.interactive_queue import OwnedInteractiveQueue, process_owned_interactive_once
        database = args.database.resolve()
        licensing = database.with_name('license.sqlite')
        if licensing.exists() or licensing.is_symlink():
            raise ValueError('This workspace contains licensing state; use the licensed local commands.')
        if args.dashboard_command == 'free-worker-cycle':
            from adaptive_qa.local_worker_cycle import process_local_cycle
            print(json.dumps(process_local_cycle(LocalFreeProjects(database))))
            return
        queue = OwnedInteractiveQueue(LocalFreeProjects(database))
        outcome = queue.recover_interrupted() if args.dashboard_command == 'free-recover-interactive' else process_owned_interactive_once(queue)
        print(outcome or 'No queued owned-fixture interactive work.')
        return
    if args.dashboard_command == 'maintenance-once':
        from adaptive_qa.project_store import ProjectStore
        from adaptive_qa.maintenance import maintenance_once
        # Reject invalid batches before creating/opening the selected database.
        if type(args.limit) is not int or not 1 <= args.limit <= 100:
            raise ValueError('Maintenance limit must be between 1 and 100.')
        print(json.dumps(maintenance_once(ProjectStore(args.database), limit=args.limit)))
        return
    if args.dashboard_command == 'recover-organization-runs':
        from adaptive_qa.project_store import ProjectStore
        from adaptive_qa.organization_store import OrganizationStore
        from adaptive_qa.organization_projects import OrganizationProjects
        from adaptive_qa.organization_discovery import OrganizationDiscoveryQueue
        from adaptive_qa.organization_runs import OrganizationRunQueue
        queue = OrganizationRunQueue(OrganizationDiscoveryQueue(OrganizationProjects(OrganizationStore(ProjectStore(args.database)))))
        print(queue.recover_interrupted())
        return
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
        if args.dashboard_command == 'recover-runs':
            print(queue.recover_interrupted())
        else:
            outcome = process_run_once(queue)
            if outcome is None:
                from adaptive_qa.organization_store import OrganizationStore
                from adaptive_qa.organization_projects import OrganizationProjects
                from adaptive_qa.organization_discovery import OrganizationDiscoveryQueue
                from adaptive_qa.organization_runs import OrganizationRunQueue
                outcome = process_run_once(OrganizationRunQueue(OrganizationDiscoveryQueue(OrganizationProjects(OrganizationStore(queue.projects)))))
            print(outcome or 'No queued test runs.')
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
    if args.dashboard_command == 'free-serve':
        from adaptive_qa.local_free import create_free_app
        app = create_free_app(args.database, port=args.port, ui_directory=ui_directory if ui_directory.is_dir() else None)
    else:
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
