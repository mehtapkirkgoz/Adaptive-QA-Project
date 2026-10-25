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


def has_unique_email(snapshot):
    """Value-free discovery eligibility; runtime still rechecks the actual field."""
    return sum(field.input_type.casefold() == 'email' and field.visible
               for form in snapshot.forms if form.visible for field in form.fields) == 1
