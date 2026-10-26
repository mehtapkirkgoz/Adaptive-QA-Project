"""Explicit demo consent, separate from permission to write to a saved target."""
from dataclasses import dataclass
import hashlib
import json

from adaptive_qa.demo_login_contract import LOGIN, DemoLoginPlan, DemoLoginScenario
from adaptive_qa.project_store import ProjectNotFound, _id


@dataclass(frozen=True)
class SavedDemoLoginReview:
    owner_id: str
    project_id: str
    configuration_fingerprint: str
    plan: DemoLoginPlan

    def __post_init__(self):
        _id(self.owner_id); _id(self.project_id)
        if (not isinstance(self.plan, DemoLoginPlan) or not isinstance(self.configuration_fingerprint, str)
                or len(self.configuration_fingerprint) != 64
                or any(c not in '0123456789abcdef' for c in self.configuration_fingerprint)):
            raise ValueError('A typed owner-scoped demo review is required.')

    def fingerprint(self):
        payload = dict(version=2, owner_id=self.owner_id, project_id=self.project_id,
            configuration_fingerprint=self.configuration_fingerprint, scenario=self.plan.scenario.value,
            document_url=LOGIN, profile='authorized_login_demo', max_submissions=1, demo_consent=True,
            post_redirect_status=303,get_redirect_status=302)
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

    def public(self):
        return dict(project_id=self.project_id, scenario=self.plan.scenario.value,
            profile='authorized_login_demo', document_url=LOGIN, execution_authorized=False,
            changes_data=True, max_submissions=1, contract_fingerprint=self.fingerprint(),
            saved_target_changed=False, uses_public_demo_account=True)


def _review_on_connection(connection, actor, project_id, *, scenario, authorized_demo):
    _id(project_id)
    if authorized_demo is not True:
        raise ValueError('Explicit permission for this exact public demo is required.')
    if not isinstance(scenario, DemoLoginScenario):
        raise ValueError('A typed demo scenario is required.')
    row = connection.execute('SELECT p.owner_id, s.settings_json FROM dashboard_projects p '
        'LEFT JOIN dashboard_project_settings s ON p.project_id=s.project_id '
        'WHERE p.project_id=? AND p.owner_id=?', (project_id, actor.user_id)).fetchone()
    if row is None: raise ProjectNotFound('Project not found.')
    # Bind changes without using, resolving, replacing or permitting writes to the
    # saved target. No configuration is required for the separate known demo.
    settings = json.loads(row['settings_json']) if row['settings_json'] else None
    revision = hashlib.sha256(json.dumps(settings, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return SavedDemoLoginReview(actor.user_id, project_id, revision, DemoLoginPlan(scenario))


def review_demo_login(projects, actor, project_id, *, scenario, authorized_demo):
    projects._actor(actor)
    with projects._connection() as connection:
        return _review_on_connection(connection, actor, project_id, scenario=scenario, authorized_demo=authorized_demo)
