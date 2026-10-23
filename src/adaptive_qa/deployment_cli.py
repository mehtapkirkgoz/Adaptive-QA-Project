"""Trusted operator deployment planning commands."""

import json
import sqlite3
from pathlib import Path
from adaptive_qa.deployment import DeploymentPlan, Environment


def configure_parser(commands):
    parser = commands.add_parser('deployment', help='Prepare non-executing deployment plans')
    plans = parser.add_subparsers(dest='deployment_command', required=True)
    for name in ('plan', 'backup', 'verify-backup', 'prepare-restore', 'rollback-plan', 'storage-health',
                 'local-prepare', 'local-select', 'local-status', 'local-run'):
        help_text = {'plan': 'Plan an environment', 'backup': 'Back up an offline environment',
                     'verify-backup': 'Verify a private offline backup without restoring it',
                     'prepare-restore': 'Restore into a fresh inactive recovery directory',
                     'rollback-plan': 'Compare a release candidate with offline schema revisions',
                     'storage-health': 'Inspect environment database storage without provisioning',
                     'local-prepare': 'Prepare a reviewed wheel/UI for the local runtime',
                     'local-select': 'Explicitly select local release/data while components are stopped',
                     'local-status': 'Inspect local release selection and component leases',
                     'local-run': 'Explicitly run a bounded loopback component'}
        plan = plans.add_parser(name, help=help_text[name])
        plan.add_argument('--environment', choices=[item.value for item in Environment], required=True)
        plan.add_argument('--data-root', type=Path, required=True)
        plan.add_argument('--origin', required=True)
        if name in ('backup', 'prepare-restore', 'rollback-plan', 'local-prepare', 'local-select'):
            plan.add_argument('--offline-maintenance', action='store_true')
        if name in ('verify-backup', 'prepare-restore'):
            plan.add_argument('--bundle-id', required=True)
        if name in ('rollback-plan', 'local-prepare'):
            plan.add_argument('--candidate', type=Path, required=True)
            plan.add_argument('--candidate-commit', required=True)
        if name == 'local-prepare':
            plan.add_argument('--trusted-release', action='store_true')
        if name == 'local-select':
            plan.add_argument('--release-id', required=True)
            data_source = plan.add_mutually_exclusive_group()
            data_source.add_argument('--recovery-id')
            data_source.add_argument('--live-data', action='store_true')
            plan.add_argument('--expected-selection')
        if name == 'local-run':
            from adaptive_qa.local_runtime import ROLES
            plan.add_argument('--role', choices=ROLES, required=True)
            plan.add_argument('--duration-seconds', type=int)


def run(args):
    plan = DeploymentPlan(Environment(args.environment), args.data_root, args.origin)
    if args.deployment_command.startswith('local-'):
        from adaptive_qa.local_runtime import prepare_local, select_local, local_status, run_local
        try:
            if args.deployment_command == 'local-prepare':
                result = prepare_local(plan, args.candidate, args.candidate_commit,
                    maintenance_confirmed=args.offline_maintenance, trusted_release=args.trusted_release)
            elif args.deployment_command == 'local-select':
                result = select_local(plan, args.release_id, recovery_id=args.recovery_id,
                    use_live_data=args.live_data,
                    expected_selection=args.expected_selection, maintenance_confirmed=args.offline_maintenance)
            elif args.deployment_command == 'local-status':
                result = local_status(plan)
            else:
                result = run_local(plan, args.role, duration_seconds=args.duration_seconds)
        except (OSError, sqlite3.Error):
            raise ValueError('Local runtime failed; review private storage, component status and release compatibility.') from None
        print(json.dumps(result, indent=2))
        if args.deployment_command == 'local-run' and result['status'] != 'completed':
            raise SystemExit(2)
    elif args.deployment_command == 'storage-health':
        from adaptive_qa.storage_health import storage_health
        result = storage_health(plan)
        print(json.dumps(result, indent=2))
        if result['status'] != 'ready':
            raise SystemExit(2)
    elif args.deployment_command == 'rollback-plan':
        from adaptive_qa.rollback_plan import plan_rollback
        try:
            result = plan_rollback(plan, args.candidate, args.candidate_commit,
                                   maintenance_confirmed=args.offline_maintenance)
        except (OSError, sqlite3.Error):
            raise ValueError('Rollback planning failed; verify the offline files and candidate bundle.') from None
        print(json.dumps(result, indent=2))
    elif args.deployment_command == 'prepare-restore':
        from adaptive_qa.backup_restore import prepare_restore
        try:
            result = prepare_restore(plan, args.bundle_id, maintenance_confirmed=args.offline_maintenance)
        except (OSError, sqlite3.Error):
            raise ValueError('Recovery preparation failed; verify offline bundle schema and private storage.') from None
        print(json.dumps(result, indent=2))
    elif args.deployment_command == 'verify-backup':
        from adaptive_qa.backup_verification import verify_backup
        try:
            result = verify_backup(plan, args.bundle_id)
        except (OSError, sqlite3.Error):
            raise ValueError('Backup verification failed; check the offline private bundle.') from None
        print(json.dumps(result, indent=2))
    elif args.deployment_command == 'backup':
        from adaptive_qa.backup import create_backup
        try:
            result = create_backup(plan, maintenance_confirmed=args.offline_maintenance)
        except (OSError, sqlite3.Error):
            raise ValueError('Backup failed; verify offline databases and private storage, then retry.') from None
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(plan.describe(), indent=2))
