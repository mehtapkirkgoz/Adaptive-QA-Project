"""Non-executing HTTPS form proposals; no worker or submission authority is granted."""
from dataclasses import asdict, dataclass
import hashlib
import json
import re
from urllib.parse import urlsplit

from adaptive_qa.config import ProjectConfig
from adaptive_qa.discovery_target import validate_discovery_project, validate_discovery_url
from adaptive_qa.interactive_contracts import FormOperation, InteractiveFormContract
from adaptive_qa.local_form_binding import LocalBooleanResponse, _name


def _public_url(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 256 or not value.isascii():
        raise ValueError('A bounded canonical HTTPS URL is required.')
    parsed = urlsplit(value)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.netloc != parsed.hostname
            or parsed.query or parsed.fragment or not re.fullmatch(r'/[A-Za-z0-9/_.-]*', parsed.path)
            or '//' in parsed.path or any(part in ('.', '..') for part in parsed.path.split('/'))):
        raise ValueError('Use an exact HTTPS URL on the default port without query or fragment.')
    project = ProjectConfig('public-form-proposal', 'Public form proposal', value, (parsed.hostname,))
    validate_discovery_project(project, 'public_https')
    return parsed.hostname


@dataclass(frozen=True)
class PublicFormProposal:
    """Reference-only intent and fixed expectations, deliberately rejected by local workers."""
    form: InteractiveFormContract
    document_url: str
    endpoint_url: str
    field_names: tuple[str, ...]
    accepted: LocalBooleanResponse
    rejected: LocalBooleanResponse

    def __post_init__(self):
        if not isinstance(self.form, InteractiveFormContract):
            raise ValueError('A typed operation contract is required.')
        host = _public_url(self.document_url)
        if _public_url(self.endpoint_url) != host or self.endpoint_url == self.document_url:
            raise ValueError('A distinct endpoint on the exact document origin is required.')
        count = 2 if self.form.operation == FormOperation.LOGIN else 1
        if type(self.field_names) is not tuple or len(self.field_names) != count:
            raise ValueError('Operation-specific typed field names are required.')
        for field in self.field_names:
            _name(field)
        if len(set(self.field_names)) != count:
            raise ValueError('Distinct field names are required.')
        if (not isinstance(self.accepted, LocalBooleanResponse)
                or not isinstance(self.rejected, LocalBooleanResponse) or self.accepted == self.rejected):
            raise ValueError('Distinct positive and negative boolean expectations are required.')

    @property
    def execution_authorized(self):
        return False

    def validate_project(self, project, *, current_fingerprint):
        self.form.validate_project(project, current_fingerprint=current_fingerprint)
        validate_discovery_project(project, 'public_https')
        host = urlsplit(self.document_url).hostname
        if project.base_url != self.document_url or project.allowed_hosts != (host,):
            raise ValueError('The proposal must match the saved single-origin project.')
        validate_discovery_url(self.endpoint_url, project, 'public_https')

    def fingerprint(self):
        payload = dict(version=1, form=self.form.fingerprint(), metadata=encode_public_proposal(self),
                       method='POST', max_submissions=1, max_body_bytes=8192,
                       max_response_bytes=1024, redirects=False, execution_authorized=False)
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def encode_public_proposal(proposal):
    if not isinstance(proposal, PublicFormProposal):
        raise ValueError('A typed non-executing proposal is required.')
    data = asdict(proposal)
    data.pop('form')
    return data


def decode_public_proposal(data, form):
    if (not isinstance(data, dict)
            or set(data) != {'document_url', 'endpoint_url', 'field_names', 'accepted', 'rejected'}
            or not isinstance(data['field_names'], list)):
        raise ValueError('Exact reference-only proposal metadata is required.')
    responses = []
    for name in ('accepted', 'rejected'):
        value = data[name]
        if not isinstance(value, dict) or set(value) != set(LocalBooleanResponse.__dataclass_fields__):
            raise ValueError('Exact boolean response expectations are required.')
        responses.append(LocalBooleanResponse(**value))
    return PublicFormProposal(form, data['document_url'], data['endpoint_url'],
                              tuple(data['field_names']), *responses)
