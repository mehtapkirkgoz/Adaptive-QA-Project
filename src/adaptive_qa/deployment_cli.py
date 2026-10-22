"""Trusted operator deployment planning commands."""

import json
from pathlib import Path
from adaptive_qa.deployment import DeploymentPlan, Environment


def configure_parser(commands):
    parser = commands.add_parser('deployment', help='Prepare non-executing deployment plans')
    plans = parser.add_subparsers(dest='deployment_command', required=True)
    plan = plans.add_parser('plan', help='Validate and describe an isolated environment without activating it')
    plan.add_argument('--environment', choices=[item.value for item in Environment], required=True)
    plan.add_argument('--data-root', type=Path, required=True)
    plan.add_argument('--origin', required=True)


def run(args):
    plan = DeploymentPlan(Environment(args.environment), args.data_root, args.origin)
    print(json.dumps(plan.describe(), indent=2))
