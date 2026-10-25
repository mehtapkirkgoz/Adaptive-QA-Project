"""Explicit read-only API review for owned loopback fixtures, without discovery."""
from dataclasses import asdict, dataclass
import hashlib
import json

from adaptive_qa.api_models import ApiCase, ApiConfiguration, HttpMethod
from adaptive_qa.config import ProjectConfig


def _fingerprint(project, case, profile='controlled_local'):
    payload = {'project': asdict(project), 'case': asdict(case)}
    if profile != 'controlled_local': payload['execution_profile'] = profile
    raw = json.dumps(payload,
                     sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True)
class LocalApiReview:
    project: ProjectConfig
    case: ApiCase
    fingerprint: str
    profile: str = 'controlled_local'

    def __post_init__(self):
        if not isinstance(self.project, ProjectConfig) or not isinstance(self.case, ApiCase):
            raise ValueError('Typed project and API case are required.')
        if self.profile not in ('controlled_local', 'public_https'):
            raise ValueError('Unknown API review profile.')
        if self.profile == 'controlled_local' and (self.project.base_url.rstrip('/') != 'http://127.0.0.1:8000'
                or self.project.allowed_hosts != ('127.0.0.1',)):
            raise ValueError('Only the explicitly owned loopback API origin is supported.')
        if (self.case.request.method not in (HttpMethod.GET, HttpMethod.HEAD)
                or self.case.request.use_authentication or self.case.request.body_json is not None
                or self.case.request.query or self.case.definition.changes_data):
            raise ValueError('This review permits unauthenticated read-only requests without input values.')
        if self.fingerprint != _fingerprint(self.project, self.case, self.profile):
            raise ValueError('API review fingerprint does not match its contracts.')
        ApiConfiguration(self.project, execution_profile=self.profile)  # Syntax only; no DNS or sockets.


def review_local_api(project, case, *, profile='controlled_local'):
    """Review explicit assertions; never infer endpoints or contact the target."""
    if not isinstance(project, ProjectConfig) or not isinstance(case, ApiCase):
        raise ValueError('Typed project and API case are required.')
    return LocalApiReview(project, case, _fingerprint(project, case, profile), profile)


def run_reviewed_local_api(review, current_project, *, confirmed_fingerprint,
                           should_cancel=None):
    """Internal operator entry point; no HTTP admission or catalog expansion."""
    if not isinstance(review, LocalApiReview) or not isinstance(current_project, ProjectConfig):
        raise ValueError('A typed current project and review are required.')
    # Reconstruct to validate even a caller-provided dataclass instance.
    LocalApiReview(review.project, review.case, review.fingerprint, review.profile)
    if (current_project != review.project
            or confirmed_fingerprint != review.fingerprint):
        raise ValueError('Current API configuration and explicit confirmation must match the review.')
    from adaptive_qa.api_process import run_isolated_api_case
    return run_isolated_api_case(review.case, ApiConfiguration(current_project, execution_profile=review.profile),
                                 timeout_seconds=15, should_cancel=should_cancel)
