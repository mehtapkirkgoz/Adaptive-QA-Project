"""Owner-scoped saved API snapshot review; never enqueue or contact a target."""
import hashlib
import json
from adaptive_qa.config import ProjectConfig
from adaptive_qa.local_api_review import review_local_api
from adaptive_qa.local_api_settings import saved_api_case
from adaptive_qa.project_settings import validate_settings
from adaptive_qa.project_store import OwnedProject, ProjectNotFound, _id


def review_saved_api(projects, actor, project_id):
    projects._actor(actor); _id(project_id)
    with projects._connection() as connection:
        return _review_api_on_connection(connection, actor, project_id)[0]


def _review_api_on_connection(connection, actor, project_id):
    row = connection.execute('SELECT p.*,s.settings_json FROM dashboard_projects p '
        'LEFT JOIN dashboard_project_settings s ON s.project_id=p.project_id '
        'WHERE p.project_id=? AND p.owner_id=?', (project_id,actor.user_id)).fetchone()
    if row is None: raise ProjectNotFound('Project not found.')
    if row['settings_json'] is None: raise ValueError('Saved API configuration is required.')
    owned = OwnedProject(row['project_id'],row['owner_id'],row['name'])
    settings = validate_settings(owned,json.loads(row['settings_json']))
    if 'local_api_binding' not in settings: raise ValueError('Saved API binding is required.')
    project = ProjectConfig(project_id,owned.name,settings['base_url'],tuple(settings['allowed_hosts']),settings['allow_data_changes'])
    review = review_local_api(project,saved_api_case(settings['local_api_binding'],project))
    snapshot = json.dumps(dict(owner_id=actor.user_id,settings=settings,contract=review.fingerprint),sort_keys=True,separators=(',',':'))
    public = dict(project_id=project_id,scope='owned_loopback_only',execution_authorized=False,
        contract_fingerprint=hashlib.sha256(snapshot.encode()).hexdigest(),
        request_method='GET',binding=settings['local_api_binding'],
        limitations=['Review does not execute, enqueue or reserve capacity.',
                     'Execution requires separate explicit confirmation and a local worker.'])
    return public, review
