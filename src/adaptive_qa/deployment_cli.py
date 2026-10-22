"""Trusted operator deployment planning commands."""

import json
import sqlite3
from pathlib import Path
from adaptive_qa.deployment import DeploymentPlan, Environment


def configure_parser(commands):
    parser = commands.add_parser('deployment', help='Prepare non-executing deployment plans')
    plans = parser.add_subparsers(dest='deployment_command', required=True)
    for name in ('plan', 'backup', 'verify-backup', 'prepare-restore', 'rollback-plan', 'storage-health'):
        help_text = {'plan': 'Plan an environment', 'backup': 'Back up an offline environment',
                     'verify-backup': 'Verify a private offline backup without restoring it',
                     'prepare-restore': 'Restore into a fresh inactive recovery directory',
                     'rollback-plan': 'Compare a release candidate with offline schema revisions',
                     'storage-health': 'Inspect environment database storage without provisioning'}
        plan = plans.add_parser(name, help=help_text[name])
        plan.add_argument('--environment', choices=[item.value for item in Environment], required=True)
        plan.add_argument('--data-root', type=Path, required=True)
        plan.add_argument('--origin', required=True)
        if name in ('backup', 'prepare-restore', 'rollback-plan'):
            plan.add_argument('--offline-maintenance', action='store_true')
        if name in ('verify-backup', 'prepare-restore'):
            plan.add_argument('--bundle-id', required=True)
        if name == 'rollback-plan':
            plan.add_argument('--candidate', type=Path, required=True)
            plan.add_argument('--candidate-commit', required=True)


def run(args):
    plan = DeploymentPlan(Environment(args.environment), args.data_root, args.origin)
    if args.deployment_command == 'storage-health':
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
