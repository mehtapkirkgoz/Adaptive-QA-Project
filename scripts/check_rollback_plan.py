"""Offline compatibility drill using a built release and disposable real stores."""

from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory

from adaptive_qa.auth_store import AuthStore
from adaptive_qa.dashboard_runs import DashboardRunQueue
from adaptive_qa.deployment import DeploymentPlan, Environment
from adaptive_qa.project_store import ProjectStore
from adaptive_qa.rollback_plan import plan_rollback
from adaptive_qa.schema_migrations import migrate_recovery_connection


ROOT = Path(__file__).resolve().parents[1]


def check(candidate):
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    candidate = Path(candidate).resolve()
    with TemporaryDirectory(prefix='adaptive-qa-rollback-drill-') as temporary:
        plan = DeploymentPlan(Environment.STAGING, Path(temporary), 'https://qa.example.test')
        AuthStore(plan.directory / 'auth.sqlite')
        DashboardRunQueue(ProjectStore(plan.directory / 'projects.sqlite'))
        for name in ('auth.sqlite', 'projects.sqlite'):
            with closing(sqlite3.connect(plan.directory / name)) as connection:
                migrate_recovery_connection(connection, name)
                connection.commit()
        before = {name: (plan.directory / name).read_bytes() for name in ('auth.sqlite', 'projects.sqlite')}
        matched = plan_rollback(plan, candidate, revision, maintenance_confirmed=True)
        assert matched['schema_compatible'] and matched['activation_enabled'] is False
        assert all((plan.directory / name).read_bytes() == value for name, value in before.items())
        with closing(sqlite3.connect(plan.directory / 'projects.sqlite')) as connection:
            connection.execute('PRAGMA user_version=2147483647')
        blocked = plan_rollback(plan, candidate, revision, maintenance_confirmed=True)
        assert blocked['schema_compatible'] is False and blocked['activation_enabled'] is False
    report = {'source_commit': revision, 'matched_current_schema': True,
              'blocked_future_schema': True, 'matched_database_bytes_unchanged': True,
              'candidate_execution': False, 'activation_enabled': False,
              'limitation': 'Declarative offline planning only; not a service or deployment rollback.'}
    output = ROOT / 'artifacts' / 'deployment' / 'rollback-plan.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    check(sys.argv[1])
