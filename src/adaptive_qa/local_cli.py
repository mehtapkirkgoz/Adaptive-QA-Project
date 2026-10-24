"""Single-device licensed commands; no central account or licensing traffic."""
import json
from pathlib import Path
from types import SimpleNamespace

from adaptive_qa.license_store import LicenseStore
from adaptive_qa.licensing import LicenseError


def _read(path, limit):
    try:
        with Path(path).open('rb') as stream:
            data = stream.read(limit+1)
        if not data or len(data) > limit:
            raise ValueError()
        return data
    except (OSError, ValueError):
        raise ValueError('Cannot read bounded local configuration file.') from None


def load_trusted_keys(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError()
            result[key] = value
        return result
    try:
        raw = json.loads(_read(path, 4096).decode('utf-8'), object_pairs_hook=unique)
        if not isinstance(raw, dict) or not 1 <= len(raw) <= 10:
            raise ValueError()
        keys = {}
        for key, value in raw.items():
            if not isinstance(value, str) or len(value) != 64:
                raise ValueError()
            keys[key] = bytes.fromhex(value)
        return keys
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise ValueError('Invalid trusted public-key configuration.') from None


def configure_parser(subparsers):
    parser = subparsers.add_parser('local', help='Manage a single-device licensed workspace')
    commands = parser.add_subparsers(dest='local_command', required=True)
    for name in ('create-admin', 'license-import', 'license-status', 'serve', 'discovery-once', 'run-once', 'interactive-once', 'recover-interactive', 'backup', 'restore'):
        command = commands.add_parser(name)
        command.add_argument('--workspace', type=Path, default=Path('artifacts/local-free'))
        if name not in ('create-admin', 'backup', 'restore'):
            command.add_argument('--trusted-keys', type=Path, required=True,
                help='Publisher public-key JSON file; never an issuer private key')
        if name in ('backup', 'restore'):
            command.add_argument('--destination', type=Path, required=True)
            command.add_argument('--maintenance-confirmed', action='store_true', help='Confirm local servers/workers are stopped')
        if name == 'restore':
            command.add_argument('--snapshot', type=Path, required=True)
        if name == 'license-import':
            command.add_argument('--license-file', type=Path, required=True)
        if name == 'serve':
            command.add_argument('--administrator', required=True, help='Previously provisioned local administrator email')
            command.add_argument('--port', type=int, default=8767)
            command.add_argument('--ui-directory', type=Path, default=Path('frontend/dist'))


def run(args):
    root = args.workspace.resolve()
    if args.local_command in ('backup', 'restore'):
        from adaptive_qa.local_backup import create_local_backup, restore_local_backup
        if args.local_command == 'backup':
            result = create_local_backup(root, args.destination.absolute(), maintenance_confirmed=args.maintenance_confirmed)
        else:
            result = restore_local_backup(args.snapshot.absolute(), args.destination.absolute(), maintenance_confirmed=args.maintenance_confirmed)
        print(json.dumps(result))
        return
    if args.local_command == 'create-admin':
        from adaptive_qa.dashboard_cli import run as dashboard_run
        dashboard_run(SimpleNamespace(dashboard_command='create-user', database=root/'auth.sqlite'))
        return
    licenses = LicenseStore(root/'license.sqlite', load_trusted_keys(args.trusted_keys))
    if args.local_command == 'license-import':
        licenses.install(_read(args.license_file, 8192))
        print('Verified local license installed. No test data was transmitted.')
        return
    if args.local_command == 'license-status':
        try:
            claims = licenses.current()
        except LicenseError:
            print(json.dumps({'status':'invalid_or_expired', 'execution_allowed':False}))
            return
        print(json.dumps({'status':'valid' if claims else 'absent', 'execution_allowed':claims is not None,
            'max_projects':claims.max_projects if claims else 0,
            'max_concurrent_runs':claims.max_concurrent_runs if claims else 0,
            'expires_at':claims.expires_at if claims else None}))
        return
    from adaptive_qa.local_licensed import LicensedLocalProjects
    projects = LicensedLocalProjects(root/'projects.sqlite', licenses)
    if args.local_command in ('interactive-once', 'recover-interactive'):
        from adaptive_qa.interactive_queue import OwnedInteractiveQueue, process_owned_interactive_once
        queue = OwnedInteractiveQueue(projects)
        outcome = queue.recover_interrupted() if args.local_command == 'recover-interactive' else process_owned_interactive_once(queue)
        print(outcome or 'No licensed interactive work available within current capacity.')
        return
    if args.local_command in ('discovery-once', 'run-once'):
        if args.local_command == 'discovery-once':
            from adaptive_qa.dashboard_jobs import DashboardDiscoveryQueue
            from adaptive_qa.dashboard_worker import process_discovery_once
            outcome = process_discovery_once(DashboardDiscoveryQueue(projects))
        else:
            from adaptive_qa.dashboard_runs import DashboardRunQueue
            from adaptive_qa.dashboard_run_worker import process_run_once
            outcome = process_run_once(DashboardRunQueue(projects))
        print(outcome or 'No licensed work available within current capacity.')
        return
    if type(args.port) is not int or not 1024 <= args.port <= 65535:
        raise ValueError('Port must be an integer in [1024, 65535].')
    from adaptive_qa.auth_store import AuthStore
    from adaptive_qa.local_licensed import create_licensed_app
    import uvicorn
    auth = AuthStore(root/'auth.sqlite')
    administrator = auth.existing_actor(args.administrator)
    if administrator is None:
        raise ValueError('Provision the designated administrator locally before serving.')
    if not args.ui_directory.is_dir():
        raise ValueError('Build the local interface before serving.')
    app = create_licensed_app(root/'projects.sqlite', auth, administrator, licenses,
        port=args.port, ui_directory=args.ui_directory)
    print(f'Licensed local dashboard: http://127.0.0.1:{args.port}/')
    uvicorn.run(app, host='127.0.0.1', port=args.port, workers=1, proxy_headers=False,
        access_log=False, log_level='warning', limit_concurrency=32, timeout_keep_alive=5)
