"""Owner-scoped, non-executing review of saved interactive fixture bindings."""
from dataclasses import dataclass
import json

from adaptive_qa.config import ProjectConfig
from adaptive_qa.dashboard_worker import configuration_fingerprint
from adaptive_qa.element_models import ElementMapping, ProjectElementMappings
from adaptive_qa.form_configuration import saved_form_mappings
from adaptive_qa.interactive_contracts import FormOperation, InteractiveFormContract
from adaptive_qa.owned_submission import FIXTURE_OPERATIONS, ORIGIN, OwnedSubmissionContract
from adaptive_qa.project_settings import reference_name, validate_settings
from adaptive_qa.project_store import OwnedProject, ProjectNotFound, _id
from adaptive_qa.secrets import SecretReference


@dataclass(frozen=True)
class SavedInteractiveReview:
    owner_id: str
    configuration: ProjectConfig
    submission: OwnedSubmissionContract
    mappings: ProjectElementMappings

    def __post_init__(self):
        _id(self.owner_id)
        if (not isinstance(self.configuration, ProjectConfig)
                or not isinstance(self.submission, OwnedSubmissionContract)
                or not isinstance(self.mappings, ProjectElementMappings)
                or self.mappings.project_id != self.configuration.project_id):
            raise ValueError("A typed saved interactive review is required.")
        self.submission.validate_project(self.configuration,
            current_fingerprint=self.submission.form.configuration_fingerprint)

    @property
    def execution_authorized(self):
        return False

    def public(self):
        return dict(project_id=self.configuration.project_id, execution_authorized=False,
                    scope="owned_fixture_only", operation=self.submission.form.operation.value,
                    changes_data=True, max_submissions=1, contract_fingerprint=self.submission.fingerprint(),
                    limitations=["Review does not enqueue, reserve capacity or authorize execution.",
                                 "Interactive execution is restricted to owned local fixtures."])


def review_saved_interactive(projects, actor, project_id, *, fixture_id, completion, timeout_seconds=15):
    """Read one owned settings snapshot, validate scoped references, never resolve them.

    This remains a review even in a licensed workspace: future queue admission must
    check the current license and reserve capacity transactionally at submit/claim.
    """
    projects._actor(actor)
    _id(project_id)
    with projects._connection() as connection:
        row=connection.execute('SELECT p.*,s.settings_json FROM dashboard_projects p '
            'LEFT JOIN dashboard_project_settings s ON s.project_id=p.project_id '
            'WHERE p.project_id=? AND p.owner_id=?',(project_id,actor.user_id)).fetchone()
        if row is None:
            raise ProjectNotFound("Project not found.")
        if row['settings_json'] is None:
            raise ValueError("Saved interactive settings are required.")
        project=OwnedProject(row['project_id'],row['owner_id'],row['name'])
        settings=validate_settings(project,json.loads(row['settings_json']))
    if not isinstance(fixture_id,str) or fixture_id not in FIXTURE_OPERATIONS:
        raise ValueError("A fixed owned interactive fixture is required.")
    operation=FIXTURE_OPERATIONS[fixture_id]
    negative=fixture_id in ('login-rejected','search-empty')
    logical=('login.rejected' if negative else 'login.accepted') if operation==FormOperation.LOGIN else ('search.empty' if negative else 'search.results')
    if not isinstance(completion,ElementMapping) or completion.logical_name!=logical:
        raise ValueError("The explicit postcondition must match the fixture outcome.")
    slots=('login_username','login_password') if operation==FormOperation.LOGIN else ('search_query',)
    references=[]
    for slot in slots:
        expected=reference_name(project.owner_id,project.project_id,slot)
        if settings['secret_references'].get(slot)!=expected:
            raise ValueError("Saved owner/project input references are required.")
        references.append(SecretReference(expected))
    config=ProjectConfig(project.project_id,project.name,settings['base_url'],tuple(settings['allowed_hosts']),settings['allow_data_changes'])
    # Unlike discovery's secret-free fingerprint, this review also binds input slot
    # references, so removing a reference invalidates a previously reviewed form.
    fingerprint=configuration_fingerprint(settings)
    form=InteractiveFormContract(project.project_id,fingerprint,operation,tuple(references),completion,timeout_seconds)
    fields=('user','password') if operation==FormOperation.LOGIN else ('query',)
    submission=OwnedSubmissionContract(form,fixture_id,config.base_url,ORIGIN+'/interactive-submit/'+fixture_id,fields)
    submission.validate_project(config,current_fingerprint=fingerprint)
    return SavedInteractiveReview(project.owner_id,config,submission,saved_form_mappings(settings['form_mappings'],project.project_id))


def revalidate_saved_interactive(projects, actor, review):
    """Reject stale/tampered reviews without executing or silently refreshing assertions."""
    if not isinstance(review,SavedInteractiveReview):
        raise ValueError("A typed saved review is required.")
    projects._actor(actor)
    if actor.user_id!=review.owner_id:
        raise ProjectNotFound("Project not found.")
    form=review.submission.form
    current=review_saved_interactive(projects,actor,form.project_id,fixture_id=review.submission.fixture_id,
        completion=form.completion,timeout_seconds=form.timeout_seconds)
    if current!=review:
        raise ValueError("Saved interactive settings changed; review them again.")
    return current
