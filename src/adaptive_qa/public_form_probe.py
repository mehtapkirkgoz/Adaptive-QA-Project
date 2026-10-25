"""Internal reviewed form probe; caller must provide a fresh, guarded disposable context."""
from time import monotonic, sleep

from adaptive_qa.form_checks import _controls
from adaptive_qa.interactive_contracts import FormOperation
from adaptive_qa.interactive_probe import InteractiveProbeResult, _valid_submit, _visible
from adaptive_qa.models import TestStatus
from adaptive_qa.owned_submission import OwnedSubmissionResult
from adaptive_qa.public_submission_process import _validate
from adaptive_qa.ui_bindings import ElementBindingError


def probe_reviewed_public_form(page, review, project, *, owner_id, current_fingerprint,
                               network_clean, before_inputs, before_submit,
                               submission_state, mappings=None):
    """Require both a verified HTTP response and the pinned UI transition, never a marker alone.

    Caller verifies the exact initial 200/text-HTML document in one fresh context,
    denies every request after input preflight except
    the one exact confirmed POST, and forwards only its verified boolean response.
    No public browser worker, queue route or screenshot capture is connected here.
    """
    armed = False
    def state():
        result = submission_state()
        if result is not None and not isinstance(result, OwnedSubmissionResult):
            raise ValueError('A sanitized submission state is required.')
        return result

    def result(status, message):
        if not armed:
            return InteractiveProbeResult(status, message, 0)
        response = state()
        return InteractiveProbeResult(status, message, response.attempted_submissions if response is not None else 0)

    try:
        _validate(review, project, owner_id, current_fingerprint)
        if not all(callable(callback) for callback in (network_clean, before_inputs, before_submit, submission_state)):
            raise ValueError()
        if page.url != project.base_url or network_clean() is not True or state() is not None:
            raise ValueError()
        contract, binding = review.proposal.form, review.proposal
        deadline = monotonic()+contract.timeout_seconds
        keys = ('login.username', 'login.password', 'login.submit') if contract.operation == FormOperation.LOGIN else ('search.query', 'search.submit')
        with _controls(page, keys, project_id=project.project_id, mappings=mappings) as controls:
            inputs, submit = controls[:-1], controls[-1]
            types = (('text', 'email'), ('password',)) if contract.operation == FormOperation.LOGIN else (('text', 'search'),)
            for control, allowed in zip(inputs, types, strict=True):
                if (not control.evaluate("el => el.tagName === 'INPUT'")
                        or control.evaluate('el => el.type') not in allowed or not control.is_editable()):
                    raise ValueError()
            if (tuple(control.get_attribute('name') for control in inputs) != binding.field_names
                    or not _valid_submit(submit, project.base_url, binding) or _visible(page, contract.completion)):
                raise ValueError()
            # The caller pins the POST peer and freezes unrelated traffic before any value is read.
            if before_inputs() is not True or network_clean() is not True:
                raise ValueError()
            values = tuple(reference.resolve().value for reference in contract.inputs)
            if any(not 1 <= len(value) <= 512 or any(ord(c) < 32 or ord(c) == 127 for c in value) for value in values):
                raise ValueError()
            for control, value in zip(inputs, values, strict=True):
                if monotonic() >= deadline or network_clean() is not True:
                    raise RuntimeError()
                control.fill(value, timeout=max(1, int((deadline-monotonic())*1000)))
            if (network_clean() is not True or page.url != project.base_url or monotonic() >= deadline):
                raise RuntimeError()
            if (not _valid_submit(submit, project.base_url, binding)
                    or tuple(control.get_attribute('name') for control in inputs) != binding.field_names
                    or _visible(page, contract.completion) or state() is not None):
                raise ValueError()
            before_submit(values)
            armed = True
            if network_clean() is not True:
                raise RuntimeError()
            submit.click(timeout=max(1, int((deadline-monotonic())*1000)))
            expected = 'accepted' if contract.completion.logical_name in ('login.accepted', 'search.results') else 'rejected'
            while monotonic() < deadline:
                if network_clean() is not True or page.url != project.base_url:
                    raise RuntimeError()
                response = state()
                if response is not None:
                    if response.outcome in ('blocked', 'error'):
                        raise RuntimeError()
                    if response.outcome != expected:
                        return result(TestStatus.FAILED, 'The reviewed HTTP outcome did not match the expected workflow.')
                    if _visible(page, contract.completion):
                        if network_clean() is not True or page.url != project.base_url:
                            raise RuntimeError()
                        return result(TestStatus.PASSED, 'The reviewed HTTP response and UI transition were verified.')
                sleep(.05)
            return result(TestStatus.FAILED, 'The reviewed response and UI transition were not both observed.')
    except (ValueError, ElementBindingError):
        try:
            return result(TestStatus.BLOCKED, 'Reviewed form preconditions were not satisfied.')
        except Exception:
            return InteractiveProbeResult(TestStatus.BLOCKED, 'Reviewed form preconditions were not satisfied.', None)
    except Exception:
        try:
            return result(TestStatus.ERROR, 'The reviewed form could not complete within its guarded scope.')
        except Exception:
            return InteractiveProbeResult(TestStatus.ERROR, 'The reviewed form could not complete within its guarded scope.', None)
