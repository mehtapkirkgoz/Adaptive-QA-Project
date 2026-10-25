"""Internal supervised HTTPS response-contract proof; no browser or queue admission."""
import argparse
from dataclasses import asdict, dataclass
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
from urllib.parse import urlencode

from adaptive_qa.browser_process import _terminate_process_tree
from adaptive_qa.config import ProjectConfig
from adaptive_qa.form_configuration import decode_form_mappings
from adaptive_qa.interactive_contracts import FormOperation, InteractiveFormContract
from adaptive_qa.local_form_binding import _unique
from adaptive_qa.owned_submission import CONTENT_TYPE
from adaptive_qa.project_settings import reference_name
from adaptive_qa.project_store import _id
from adaptive_qa.public_form_proposal import encode_public_proposal, decode_public_proposal
from adaptive_qa.public_submission import PublicSubmissionTransport, ReviewedPublicForm
from adaptive_qa.secrets import SecretReference


REASONS = {
    'accepted': {'response_accepted'}, 'rejected': {'response_rejected'},
    'blocked': {'preconditions_blocked'},
    'error': {'transport_error', 'deadline_exceeded', 'cancellation_source_failed',
              'child_start_failed', 'child_failed', 'invalid_child_result'},
    'cancelled': {'cancelled'},
}


@dataclass(frozen=True)
class SubmissionProcessResult:
    outcome: str
    reason_code: str
    attempted_submissions: int | None

    def __post_init__(self):
        if (not isinstance(self.outcome, str) or not isinstance(self.reason_code, str)
                or self.outcome not in REASONS or self.reason_code not in REASONS[self.outcome]
                or (self.attempted_submissions is not None and
                    (type(self.attempted_submissions) is not int or self.attempted_submissions not in (0, 1)))
                or (self.outcome in ('accepted', 'rejected') and self.attempted_submissions != 1)
                or (self.outcome == 'blocked' and self.attempted_submissions != 0)
                or (self.outcome == 'cancelled' and self.attempted_submissions == 1)):
            raise ValueError('Invalid sanitized response-contract outcome.')


def _validate(review, project, owner_id, fingerprint):
    if not isinstance(review, ReviewedPublicForm):
        raise ValueError('An explicit reviewed proposal is required.')
    _id(owner_id)
    review.validate_project(project, current_fingerprint=fingerprint)
    slots = ('login_username', 'login_password') if review.proposal.form.operation == FormOperation.LOGIN else ('search_query',)
    if tuple(ref.environment_variable for ref in review.proposal.form.inputs) != tuple(
            reference_name(owner_id, project.project_id, slot) for slot in slots):
        raise ValueError('Input references must match the exact owner/project slots.')


def _encode(review, project, owner_id, fingerprint):
    _validate(review, project, owner_id, fingerprint)
    raw = json.dumps(dict(contract=asdict(review.proposal.form), proposal=encode_public_proposal(review.proposal),
        confirmed_fingerprint=review.confirmed_fingerprint, project=asdict(project), owner_id=owner_id,
        current_fingerprint=fingerprint), ensure_ascii=True)
    if len(raw.encode('utf-8')) > 16384:
        raise ValueError('Oversized private response-contract metadata.')
    return raw


def _decode(raw):
    if not isinstance(raw, str) or len(raw.encode('utf-8')) > 16384:
        raise ValueError('Bounded metadata is required.')
    data = json.loads(raw, object_pairs_hook=_unique)
    if not isinstance(data, dict) or set(data) != {'contract', 'proposal', 'confirmed_fingerprint', 'project', 'owner_id', 'current_fingerprint'}:
        raise ValueError('Exact response-contract fields are required.')
    c, p = data['contract'], data['project']
    if (not isinstance(c, dict) or set(c) != set(InteractiveFormContract.__dataclass_fields__)
            or not isinstance(c['inputs'], list) or not isinstance(p, dict)
            or set(p) != set(ProjectConfig.__dataclass_fields__) or not isinstance(p['allowed_hosts'], list)):
        raise ValueError('Typed project and contract metadata are required.')
    references = []
    for reference in c['inputs']:
        if not isinstance(reference, dict) or set(reference) != {'environment_variable'}:
            raise ValueError('Only input references are allowed.')
        references.append(SecretReference(**reference))
    completion = decode_form_mappings({'project_id': c['project_id'], 'mappings': [c['completion']]}).mappings[0]
    form = InteractiveFormContract(c['project_id'], c['configuration_fingerprint'], FormOperation(c['operation']),
                                   tuple(references), completion, c['timeout_seconds'])
    proposal = decode_public_proposal(data['proposal'], form)
    review = ReviewedPublicForm(proposal, data['confirmed_fingerprint'])
    project = ProjectConfig(**{**p, 'allowed_hosts': tuple(p['allowed_hosts'])})
    _validate(review, project, data['owner_id'], data['current_fingerprint'])
    return review, project, data['owner_id'], data['current_fingerprint']


def _execute(review, project, owner_id, fingerprint):
    _validate(review, project, owner_id, fingerprint)
    transport = PublicSubmissionTransport(review, project, current_fingerprint=fingerprint)
    # The complete DNS answer set is checked and its peer pinned before reading inputs.
    if not transport.prepare_destination():
        return SubmissionProcessResult('blocked', 'preconditions_blocked', 0)
    try:
        values = tuple(reference.resolve().value for reference in review.proposal.form.inputs)
        if any(not 1 <= len(value) <= 512 or any(ord(c) < 32 or ord(c) == 127 for c in value) for value in values):
            raise ValueError()
    except ValueError:
        return SubmissionProcessResult('blocked', 'preconditions_blocked', 0)
    body = urlencode(tuple(zip(review.proposal.field_names, values, strict=True))).encode('ascii')
    result = transport.submit(url=review.proposal.endpoint_url, method='POST', content_type=CONTENT_TYPE, body=body)
    reason = {'accepted': 'response_accepted', 'rejected': 'response_rejected',
              'blocked': 'preconditions_blocked', 'error': 'transport_error'}[result.outcome]
    return SubmissionProcessResult(result.outcome, reason, result.attempted_submissions)


def _read_result(path):
    if path.resolve() != path or not path.is_file() or path.stat().st_nlink != 1:
        raise ValueError('Invalid child result path.')
    with path.open('rb') as stream:
        raw = stream.read(4097)
    if len(raw) > 4096:
        raise ValueError('Oversized child result.')
    data = json.loads(raw, object_pairs_hook=_unique)
    if not isinstance(data, dict) or set(data) != set(SubmissionProcessResult.__dataclass_fields__):
        raise ValueError('Invalid child result fields.')
    result = SubmissionProcessResult(**data)
    if result.reason_code not in {'response_accepted', 'response_rejected', 'preconditions_blocked', 'transport_error'}:
        raise ValueError('Unexpected child result code.')
    return result


def run_isolated_public_submission(review, project, *, owner_id, current_fingerprint,
                                    timeout_seconds=45, should_cancel=None):
    raw = _encode(review, project, owner_id, current_fingerprint)
    if (isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 45
            or (should_cancel is not None and not callable(should_cancel))):
        raise ValueError('A finite deadline and trusted cancellation callback are required.')
    started = perf_counter()
    def stopped():
        try:
            if should_cancel is not None and should_cancel():
                return SubmissionProcessResult('cancelled', 'cancelled', None)
        except Exception:
            return SubmissionProcessResult('error', 'cancellation_source_failed', None)
        return None
    initial = stopped()
    if initial:
        return SubmissionProcessResult(initial.outcome, initial.reason_code, 0)
    with TemporaryDirectory(prefix='adaptive-public-submit-') as temporary:
        root = Path(temporary).resolve(strict=True)
        source, output = root/'input.json', root/'result.json'
        source.write_text(raw, encoding='utf-8')
        options = {'start_new_session': True} if os.name != 'nt' else {
            'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
        environment = dict(os.environ)
        environment.pop('SSLKEYLOGFILE', None)
        try:
            process = subprocess.Popen([sys.executable, '-m', 'adaptive_qa.public_submission_process',
                '--input', str(source), '--output', str(output)], stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, env=environment, **options)
        except OSError:
            return SubmissionProcessResult('error', 'child_start_failed', 0)
        try:
            while True:
                stop = stopped()
                if stop:
                    return stop
                remaining = timeout_seconds-(perf_counter()-started)
                if remaining <= 0:
                    return SubmissionProcessResult('error', 'deadline_exceeded', None)
                try:
                    process.wait(timeout=min(.2, remaining))
                    break
                except subprocess.TimeoutExpired:
                    continue
            if process.returncode != 0:
                return SubmissionProcessResult('error', 'child_failed', None)
            try:
                return _read_result(output)
            except (OSError, ValueError, TypeError, KeyError, RecursionError):
                return SubmissionProcessResult('error', 'invalid_child_result', None)
        finally:
            if process.poll() is None:
                _terminate_process_tree(process)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    source, output = Path(args.input), Path(args.output)
    if (source.resolve() != source or output.resolve() != output or source.parent != output.parent
            or source.name != 'input.json' or output.name != 'result.json'
            or not source.is_file() or source.stat().st_nlink != 1 or output.exists()):
        raise ValueError('Private canonical sibling transport paths are required.')
    with source.open('rb') as stream:
        raw = stream.read(16385)
    result = _execute(*_decode(raw.decode('utf-8')))
    with output.open('x', encoding='utf-8') as stream:
        json.dump(asdict(result), stream)


if __name__ == '__main__':
    main()
