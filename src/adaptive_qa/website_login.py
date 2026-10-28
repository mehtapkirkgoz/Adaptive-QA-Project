"""Conservative, value-free login discovery and an explicit saved-site review."""
from dataclasses import dataclass
import hashlib
import json
from urllib.parse import urlsplit

from adaptive_qa.dashboard_worker import configuration_fingerprint
from adaptive_qa.discovery_target import configured_discovery, validate_discovery_url
from adaptive_qa.project_store import ProjectNotFound, _id


def login_candidate(pages, project, profile):
    """Only inspected password forms qualify; absence is never site-wide proof."""
    candidates = []
    for page in pages:
        validate_discovery_url(page.url, project, profile)
        for form in page.forms:
            fields = [f for f in form.fields if f.visible]
            passwords = [f for f in fields if f.input_type == 'password']
            identifiers = [f for f in fields if f.input_type in ('email', 'text')]
            if (not form.visible or len(passwords) != 1 or len(identifiers) != 1
                    or passwords[0].autocomplete == 'new-password'):
                continue
            words = ' '.join((form.form_id, *form.buttons)).lower()
            if any(word in words for word in ('register', 'sign up', 'signup', 'reset', 'create account')):
                continue
            if (passwords[0].autocomplete != 'current-password'
                    and not any(word in words for word in ('login','log in','signin','sign in','giriş','giris'))):
                continue
            field = identifiers[0]
            kind = 'email' if field.input_type == 'email' or 'email' in field.label.lower() else 'username'
            candidates.append(dict(document_url=page.url, identifier_kind=kind))
    unique = candidates
    return dict(status='found' if len(unique) == 1 else 'ambiguous' if unique else 'not_found',
                candidate=unique[0] if len(unique) == 1 else None,
                scope='inspected_pages_only')


@dataclass(frozen=True)
class SavedWebsiteLoginReview:
    owner_id: str
    project_id: str
    check_id: str
    configuration_fingerprint: str
    document_url: str
    identifier_kind: str

    def fingerprint(self):
        from dataclasses import asdict
        return hashlib.sha256(json.dumps(dict(version=1, **asdict(self)), sort_keys=True).encode()).hexdigest()

    def public(self):
        return dict(project_id=self.project_id, check_id=self.check_id, document_url=self.document_url,
                    identifier_kind=self.identifier_kind, contract_fingerprint=self.fingerprint(),
                    max_submissions=1, execution_authorized=False, changes_data=True,
                    scope='standard_same_origin_html_login', credentials_persisted=False)


def _review_on_connection(connection, actor, project_id, check_id):
    _id(project_id); _id(check_id)
    row = connection.execute('SELECT c.*, s.settings_json FROM dashboard_site_checks c '
        'JOIN dashboard_projects p ON p.project_id=c.project_id AND p.owner_id=c.owner_id '
        'JOIN dashboard_project_settings s ON s.project_id=p.project_id '
        'WHERE c.check_id=? AND c.project_id=? AND c.owner_id=?',
        (check_id, project_id, actor.user_id)).fetchone()
    if row is None:
        raise ProjectNotFound('Site check not found.')
    if row['status'] not in ('completed', 'no_tests'):
        raise ValueError('Finish the read-only website check first.')
    settings = json.loads(row['settings_json'])
    # A check of a previous saved target can never authorize the new target.
    if settings['base_url'] != row['url']:
        raise ValueError('The saved website changed. Inspect it again.')
    summary = json.loads(row['summary_json'])
    detected = summary.get('login', {})
    if detected.get('status') != 'found':
        raise ValueError('One unambiguous login form must be inspected first.')
    candidate = detected['candidate']
    profile, project = configured_discovery(settings, project_id=project_id)
    if profile != 'public_https':
        raise ValueError('Website credentials require public HTTPS.')
    validate_discovery_url(candidate['document_url'], project, profile)
    if urlsplit(candidate['document_url']).netloc != urlsplit(project.base_url).netloc:
        raise ValueError('Login must use the exact saved website origin.')
    if candidate['identifier_kind'] not in ('email', 'username'):
        raise ValueError('Unsupported login identifier.')
    return SavedWebsiteLoginReview(actor.user_id, project_id, check_id,
        configuration_fingerprint(settings), candidate['document_url'], candidate['identifier_kind'])


def review_website_login(projects, actor, project_id, check_id):
    projects._actor(actor)
    with projects._connection() as connection:
        return _review_on_connection(connection, actor, project_id, check_id)
