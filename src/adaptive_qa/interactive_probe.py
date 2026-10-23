"""Internal controlled DOM probe; not a queued/subprocess or external submission worker."""
from dataclasses import dataclass
from time import monotonic, sleep

from adaptive_qa.discovery_target import validate_discovery_project
from adaptive_qa.element_matching import match_element
from adaptive_qa.element_models import MatchStatus
from adaptive_qa.form_checks import _controls
from adaptive_qa.interactive_contracts import InteractiveFormContract, FormOperation
from adaptive_qa.models import TestStatus
from adaptive_qa.ui_bindings import ElementBindingError


@dataclass(frozen=True)
class InteractiveProbeResult:
    status: TestStatus
    message: str
    attempted_submissions: int


def _visible(page, mapping):
    bound = match_element(page,mapping)
    try:
        if bound.result.status in (MatchStatus.AMBIGUOUS,MatchStatus.ERROR):
            raise ElementBindingError(bound.result)
        return bound.result.status==MatchStatus.MATCHED and bound.handle.is_visible()
    finally:
        bound.close()


def _valid_submit(submit,url):
    return submit.evaluate("""(el,url)=>el.isConnected && el.form && ['BUTTON','INPUT'].includes(el.tagName)
    && el.type==='submit' && !el.disabled && (el.hasAttribute('formaction')?el.formAction:el.form.action)===url
    && (el.hasAttribute('formmethod')?el.formMethod:el.form.method).toLowerCase()==='get'
    && ['', '_self'].includes(el.hasAttribute('formtarget')?el.formTarget:el.form.target)""",url)


def probe_controlled_form(page,contract,project,*,current_fingerprint,network_clean,mappings=None):
    """Caller must own a fresh no-network context and dispose it without screenshots/tracing."""
    attempted = 0
    try:
        if not isinstance(contract,InteractiveFormContract) or not callable(network_clean):
            raise ValueError()
        contract.validate_project(project,current_fingerprint=current_fingerprint)
        validate_discovery_project(project,'controlled_local')
        if page.url!=project.base_url or not network_clean(): raise ValueError()
        deadline = monotonic()+contract.timeout_seconds
        keys = ('login.username','login.password','login.submit') if contract.operation==FormOperation.LOGIN else ('search.query','search.submit')
        with _controls(page,keys,project_id=project.project_id,mappings=mappings) as handles:
            inputs,submit = handles[:-1],handles[-1]
            types = (('text','email'),('password',)) if contract.operation==FormOperation.LOGIN else (('text','search'),)
            for control,allowed in zip(inputs,types,strict=True):
                if not control.evaluate("el=>el.tagName==='INPUT'") or control.get_attribute('type') not in (*allowed,None):
                    raise ValueError()
                # An omitted type is valid for text inputs only, never for passwords.
                if allowed==('password',) and control.get_attribute('type')!='password': raise ValueError()
                if not control.is_enabled(): raise ValueError()
            valid = _valid_submit(submit,project.base_url)
            if not valid or _visible(page,contract.completion): raise ValueError()
            # Resolve only after project, controls, action/method and precondition validation.
            values = [reference.resolve() for reference in contract.inputs]
            if any(len(value.value)>512 or any(ord(c)<32 for c in value.value) for value in values): raise ValueError()
            for control,value in zip(inputs,values,strict=True):
                if monotonic()>=deadline or not network_clean(): raise RuntimeError()
                control.fill(value.value,timeout=max(1,int((deadline-monotonic())*1000)))
            if not network_clean() or page.url!=project.base_url or monotonic()>=deadline: raise RuntimeError()
            if not _valid_submit(submit,project.base_url) or _visible(page,contract.completion): raise ValueError()
            attempted = 1
            submit.click(timeout=max(1,int((deadline-monotonic())*1000)))
            while monotonic()<deadline:
                if not network_clean() or page.url!=project.base_url: raise RuntimeError()
                if _visible(page,contract.completion):
                    return InteractiveProbeResult(TestStatus.PASSED,'Controlled form transition verified.',attempted)
                sleep(.05)
            return InteractiveProbeResult(TestStatus.FAILED,'Expected controlled form transition was not observed.',attempted)
    except (ValueError,ElementBindingError):
        return InteractiveProbeResult(TestStatus.BLOCKED,'Controlled form preconditions were not satisfied.',attempted)
    except Exception:
        # Playwright exceptions can contain filled values; never expose their text.
        return InteractiveProbeResult(TestStatus.ERROR,'Controlled form probe could not complete.',attempted)
