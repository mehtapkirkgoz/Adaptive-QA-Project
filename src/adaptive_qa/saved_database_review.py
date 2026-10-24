"""One owned saved snapshot; reviewing never resolves or opens a target database."""
from dataclasses import asdict,dataclass
import hashlib
import json
from adaptive_qa.config import ProjectConfig
from adaptive_qa.database_models import DatabaseConfiguration
from adaptive_qa.local_database_settings import DatabaseCountBinding,database_count_case
from adaptive_qa.project_settings import validate_settings
from adaptive_qa.project_store import OwnedProject, ProjectNotFound, _id
from adaptive_qa.secrets import SecretReference


@dataclass(frozen=True)
class SavedDatabaseExecution:
    configuration: DatabaseConfiguration
    binding: DatabaseCountBinding

    def __post_init__(self):
        database_count_case(self.configuration,self.binding)

    @property
    def case(self):
        return database_count_case(self.configuration,self.binding)


def review_saved_database(projects,actor,project_id):
    projects._actor(actor);_id(project_id)
    with projects._connection() as connection:
        return _review_database_on_connection(connection,actor,project_id)[0]


def _review_database_on_connection(connection,actor,project_id):
    row=connection.execute('SELECT p.*,s.settings_json FROM dashboard_projects p '
        'LEFT JOIN dashboard_project_settings s ON s.project_id=p.project_id '
        'WHERE p.project_id=? AND p.owner_id=?',(project_id,actor.user_id)).fetchone()
    if row is None:raise ProjectNotFound('Project not found.')
    if row['settings_json'] is None:raise ValueError('Saved database configuration is required.')
    owned=OwnedProject(row['project_id'],row['owner_id'],row['name'])
    settings=validate_settings(owned,json.loads(row['settings_json']))
    if 'local_database_binding' not in settings or 'database_path' not in settings['secret_references']:
        raise ValueError('A saved count binding and scoped database reference are required.')
    binding=DatabaseCountBinding(**settings['local_database_binding'])
    project=ProjectConfig(project_id,owned.name,settings['base_url'],tuple(settings['allowed_hosts']),settings['allow_data_changes'])
    configuration=DatabaseConfiguration(project,SecretReference(settings['secret_references']['database_path']))
    snapshot=json.dumps(dict(owner_id=actor.user_id,settings=settings,configuration=asdict(configuration)),
        sort_keys=True,separators=(',',':'))
    public=dict(project_id=project_id,execution_authorized=False,scope='owned_workspace_fixtures_only',
        contract_fingerprint=hashlib.sha256(snapshot.encode()).hexdigest(),binding=asdict(binding),
        database_reference_configured=True,
        limitations=['Review does not resolve the database path, open SQLite, enqueue or reserve capacity.',
            'HTTP admission and customer worker commands are not enabled.'])
    return public,SavedDatabaseExecution(configuration,binding)
