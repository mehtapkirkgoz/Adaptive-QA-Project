"""Native browser validity probes on detached controls; no page input events or submission."""
from functools import partial


class NativeFormUnavailable(ValueError):
    """No unique participating control; no website assertion can be made."""


def check_email(page, *, valid, project_id=None, mappings=None):
    # A detached clone preserves the site's constraints without changing live fields,
    # running input handlers, reading existing values or submitting a form.
    controls = page.locator('input[type="email"]:visible:not(:disabled):not([readonly])')
    if controls.count() != 1:
        raise NativeFormUnavailable()
    outcome = controls.evaluate_all("""(elements, valid) => {
        const probe = elements[0].cloneNode(false);
        probe.removeAttribute('value');
        probe.value = valid ? 'qa@example.test' : 'invalid';
        return {candidate: probe.willValidate, valid: probe.validity.valid,
                typeMismatch: probe.validity.typeMismatch};
    }""", valid)
    if not outcome['candidate']:
        raise NativeFormUnavailable()
    assert outcome['valid'] if valid else outcome['typeMismatch'], 'Native email validity did not match the expected outcome.'


NATIVE_FORM_CHECKS = {
    'FORM-001': partial(check_email, valid=False),
    'FORM-002': partial(check_email, valid=True),
}


def check_number_bound(page, *, minimum, project_id=None, mappings=None):
    controls=page.locator('input[type="number"]:visible:not(:disabled):not([readonly])')
    if controls.count()!=1:raise NativeFormUnavailable()
    outcome=controls.evaluate_all(r'''(elements, minimum) => {
        const probe=elements[0].cloneNode(false);
        probe.removeAttribute('value');
        const raw=probe.getAttribute(minimum?'min':'max');
        if (!raw || !/^-?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(raw)) return null;
        const bound=Number(raw);
        if (!Number.isFinite(bound) || Math.abs(bound)>1e12 || !probe.willValidate) return null;
        probe.valueAsNumber=bound+(minimum?-1:1);
        return {matched:minimum?probe.validity.rangeUnderflow:probe.validity.rangeOverflow};
    }''',minimum)
    if outcome is None:raise NativeFormUnavailable()
    assert outcome['matched'],'Native number range validity did not match the declared bound.'


NATIVE_NUMBER_CHECKS={'FORM-008':partial(check_number_bound,minimum=True),
                      'FORM-009':partial(check_number_bound,minimum=False)}
NATIVE_FORM_CHECKS.update(NATIVE_NUMBER_CHECKS)


def has_unique_email(snapshot):
    """Value-free discovery eligibility; runtime still rechecks the actual field."""
    return sum(field.input_type.casefold() == 'email' and field.visible
               for form in snapshot.forms if form.visible for field in form.fields) == 1


def has_native_candidate(snapshot,case_id):
    if case_id not in NATIVE_NUMBER_CHECKS:return case_id in ('FORM-001','FORM-002') and has_unique_email(snapshot)
    fields=[field for form in snapshot.forms if form.visible for field in form.fields
            if field.visible and field.input_type.casefold()=='number']
    return len(fields)==1 and (fields[0].native_minimum if case_id=='FORM-008' else fields[0].native_maximum)
