"""Trusted operator deployment planning commands."""

import json
import sqlite3
from pathlib import Path
from adaptive_qa.deployment import DeploymentPlan, Environment


def configure_parser(commands):
    parser = commands.add_parser('deployment', help='Prepare non-executing deployment plans')
    plans = parser.add_subparsers(dest='deployment_command', required=True)
    for name in ('plan', 'backup'):
        plan = plans.add_parser(name, help='Plan an environment' if name == 'plan' else 'Back up an offline environment')
        plan.add_argument('--environment', choices=[item.value for item in Environment], required=True)
        plan.add_argument('--data-root', type=Path, required=True)
        plan.add_argument('--origin', required=True)
        if name == 'backup':
            plan.add_argument('--offline-maintenance', action='store_true')


def run(args):
    plan = DeploymentPlan(Environment(args.environment), args.data_root, args.origin)
    if args.deployment_command == 'backup':
        from adaptive_qa.backup import create_backup
        try:
            result = create_backup(plan, maintenance_confirmed=args.offline_maintenance)
        except (OSError, sqlite3.Error):
            raise ValueError('Backup failed; verify offline databases and private storage, then retry.') from None
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(plan.describe(), indent=2))
