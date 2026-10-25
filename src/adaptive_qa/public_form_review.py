"""Non-executing personal-project review of explicitly saved HTTPS form metadata."""
from dataclasses import dataclass
import json

from adaptive_qa.config import ProjectConfig
from adaptive_qa.dashboard_worker import configuration_fingerprint
from adaptive_qa.element_models import ElementMapping, ProjectElementMappings
from adaptive_qa.form_configuration import saved_form_mappings
from adaptive_qa.interactive_contracts import FormOperation, InteractiveFormContract
from adaptive_qa.project_settings import reference_name, validate_settings
from adaptive_qa.project_store import OwnedProject, ProjectNotFound, _id
from adaptive_qa.public_form_proposal import PublicFormProposal, decode_public_proposal
from adaptive_qa.public_submission import ReviewedPublicForm
from adaptive_qa.public_submission_process import _validate
from adaptive_qa.secrets import SecretReference


@dataclass(frozen=True)
class SavedPublicFormReview:
    owner_id: str
    configuration: ProjectConfig
    submission: PublicFormProposal
    mappings: ProjectElementMappings

    def __post_init__(self):
        _id(self.owner_id)
        if (not isinstance(self.submission, PublicFormProposal)
                or not isinstance(self.mappings, ProjectElementMappings)
                or not isinstance(self.configuration, ProjectConfig)
                or self.mappings.project_id != self.configuration.project_id):
            raise ValueError('A typed owner-scoped saved HTTPS review is required.')
        wrapper = ReviewedPublicForm(self.submission, self.submission.fingerprint())
        _validate(wrapper, self.configuration, self.owner_id, self.submission.form.configuration_fingerprint)

    @property
    def execution_authorized(self):return False

    def public(self):
        return dict(project_id=self.configuration.project_id, execution_authorized=False,
            profile='public_https', scope='saved_https_form_review', operation=self.submission.form.operation.value,
            document_url=self.submission.document_url, endpoint_url=self.submission.endpoint_url,
            changes_data=True, max_submissions=1, contract_fingerprint=self.submission.fingerprint(),
            screenshots=False, limitations=[
                'Review never enqueues, reserves capacity, resolves inputs or contacts the target.',
                'One same-origin POST and exact boolean JSON/UI expectations; no redirects or cookies.',
                'The authenticated queue/admission integration is not enabled by this review.'])


def _review_on_connection(connection, actor, project_id, *, completion, timeout_seconds=15):
    row=connection.execute('SELECT p.*,s.settings_json FROM dashboard_projects p '
        'LEFT JOIN dashboard_project_settings s ON s.project_id=p.project_id '
        'WHERE p.project_id=? AND p.owner_id=?',(project_id,actor.user_id)).fetchone()
    if row is None:raise ProjectNotFound('Project not found.')
    if row['settings_json'] is None:raise ValueError('Saved HTTPS workflow settings are required.')
    project=OwnedProject(row['project_id'],row['owner_id'],row['name'])
    settings=validate_settings(project,json.loads(row['settings_json']))
    raw=settings.get('local_form_binding')
    if not isinstance(raw,dict) or raw.get('profile')!='public_https':
        raise ValueError('Explicit saved public HTTPS form metadata is required.')
    operation=FormOperation(raw['operation'])
    if not isinstance(completion,ElementMapping):raise ValueError('An explicit UI completion mapping is required.')
    slots=('login_username','login_password') if operation==FormOperation.LOGIN else ('search_query',)
    references=[]
    for slot in slots:
        expected=reference_name(project.owner_id,project.project_id,slot)
        if settings['secret_references'].get(slot)!=expected:
            raise ValueError('Exact saved owner/project input reference slots are required.')
        references.append(SecretReference(expected))
    fingerprint=configuration_fingerprint(settings)
    form=InteractiveFormContract(project.project_id,fingerprint,operation,tuple(references),completion,timeout_seconds)
    proposal=decode_public_proposal({key:value for key,value in raw.items() if key not in ('operation','profile')},form)
    config=ProjectConfig(project.project_id,project.name,settings['base_url'],tuple(settings['allowed_hosts']),settings['allow_data_changes'])
    return SavedPublicFormReview(project.owner_id,config,proposal,saved_form_mappings(settings['form_mappings'],project.project_id))


def review_saved_public_form(projects, actor, project_id, *, completion, timeout_seconds=15):
    projects._actor(actor);_id(project_id)
    with projects._connection() as connection:
        return _review_on_connection(connection,actor,project_id,completion=completion,timeout_seconds=timeout_seconds)


def revalidate_saved_public_form(projects, actor, review):
    projects._actor(actor)
    if not isinstance(review,SavedPublicFormReview):raise ValueError('A saved HTTPS review is required.')
    if actor.user_id!=review.owner_id:raise ProjectNotFound('Project not found.')
    form=review.submission.form
    current=review_saved_public_form(projects,actor,form.project_id,completion=form.completion,timeout_seconds=form.timeout_seconds)
    if current!=review:raise ValueError('Saved HTTPS workflow changed; review it again.')
    return current
