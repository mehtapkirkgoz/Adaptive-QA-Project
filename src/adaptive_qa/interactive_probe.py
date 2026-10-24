"""Internal controlled DOM probe; optional supervision lives in interactive_process."""
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
    attempted_submissions: int | None

    def __post_init__(self):
        if (not isinstance(self.status,TestStatus) or not isinstance(self.message,str)
                or not 1<=len(self.message)<=160
                or (self.attempted_submissions is not None and (type(self.attempted_submissions) is not int or self.attempted_submissions not in (0,1)))):
            raise ValueError("Invalid sanitized interactive result.")


def _visible(page, mapping):
    bound = match_element(page,mapping)
    try:
        if bound.result.status in (MatchStatus.AMBIGUOUS,MatchStatus.ERROR):
            raise ElementBindingError(bound.result)
        return bound.result.status==MatchStatus.MATCHED and bound.handle.is_visible()
    finally:
        bound.close()


def _valid_submit(submit,url,submission=None):
    if submission is not None:
        return submit.evaluate("""(el,binding)=>el.isConnected && el.form && ['BUTTON','INPUT'].includes(el.tagName)
        && el.type==='submit' && !el.disabled
        && (el.hasAttribute('formaction')?el.formAction:el.form.action)===binding.url
        && (el.hasAttribute('formmethod')?el.formMethod:el.form.method).toLowerCase()==='post'
        && (el.hasAttribute('formenctype')?el.formEnctype:el.form.enctype)==='application/x-www-form-urlencoded'
        && ['','_self'].includes(el.hasAttribute('formtarget')?el.formTarget:el.form.target)""", {"url":submission.endpoint_url})
    return submit.evaluate("""(el,url)=>el.isConnected && el.form && ['BUTTON','INPUT'].includes(el.tagName)
    && el.type==='submit' && !el.disabled && (el.hasAttribute('formaction')?el.formAction:el.form.action)===url
    && (el.hasAttribute('formmethod')?el.formMethod:el.form.method).toLowerCase()==='get'
    && ['', '_self'].includes(el.hasAttribute('formtarget')?el.formTarget:el.form.target)""",url)


def probe_controlled_form(page,contract,project,*,current_fingerprint,network_clean,mappings=None,submission=None,before_submit=None):
    """Caller owns a fresh guarded context; only a typed owned binding may submit."""
    attempted = 0
    try:
        if not isinstance(contract,InteractiveFormContract) or not callable(network_clean):
            raise ValueError()
        contract.validate_project(project,current_fingerprint=current_fingerprint)
        if submission is not None:
            from adaptive_qa.owned_submission import OwnedSubmissionContract
            from adaptive_qa.local_form_binding import LocalFormBinding
            if not isinstance(submission,(OwnedSubmissionContract,LocalFormBinding)) or submission.form!=contract or not callable(before_submit): raise ValueError()
            submission.validate_project(project,current_fingerprint=current_fingerprint)
        elif before_submit is not None: raise ValueError()
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
            if submission is not None and tuple(control.get_attribute('name') for control in inputs)!=submission.field_names: raise ValueError()
            valid = _valid_submit(submit,project.base_url,submission)
            if not valid or _visible(page,contract.completion): raise ValueError()
            # Resolve only after project, controls, action/method and precondition validation.
            values = [reference.resolve() for reference in contract.inputs]
            if any(len(value.value)>512 or any(ord(c)<32 for c in value.value) for value in values): raise ValueError()
            for control,value in zip(inputs,values,strict=True):
                if monotonic()>=deadline or not network_clean(): raise RuntimeError()
                control.fill(value.value,timeout=max(1,int((deadline-monotonic())*1000)))
            if not network_clean() or page.url!=project.base_url or monotonic()>=deadline: raise RuntimeError()
            if not _valid_submit(submit,project.base_url,submission) or _visible(page,contract.completion): raise ValueError()
            if submission is not None:
                if tuple(control.get_attribute('name') for control in inputs)!=submission.field_names: raise ValueError()
                before_submit(tuple(value.value for value in values))
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
