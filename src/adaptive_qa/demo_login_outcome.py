"""Bounded diagnostic codes, never response text or cookies."""
from dataclasses import dataclass
import re
from adaptive_qa.public_submission_process import SubmissionProcessResult


PREFIX = 'Authorized demo diagnostic: '
CODES = {'demo_redirect_blocked','demo_response_too_large','demo_tls_failed',
         'demo_destination_blocked','demo_network_error','demo_browser_incomplete',
         'demo_unexpected_response','transport_error','deadline_exceeded',
         'cancellation_source_failed','child_start_failed','child_failed','invalid_child_result'}


def valid_diagnostic(code):
    return isinstance(code,str) and (code in CODES or re.fullmatch(r'http_status_[1-5][0-9]{2}',code) is not None)


def diagnostic_from_message(message):
    if not isinstance(message,str) or not message.startswith(PREFIX):return None
    code=message[len(PREFIX):]
    return code if valid_diagnostic(code) else None


class DemoTransportError(ValueError):
    def __init__(self,code):
        if not valid_diagnostic(code):raise ValueError('Invalid demo diagnostic.')
        self.code=code
        super().__init__(code)


@dataclass(frozen=True)
class DemoProcessResult:
    outcome: str
    reason_code: str
    attempted_submissions: int | None

    def __post_init__(self):
        # Keep the existing outcome/count contract; only error reasons are extended.
        reason='transport_error' if self.outcome=='error' and valid_diagnostic(self.reason_code) else self.reason_code
        SubmissionProcessResult(self.outcome,reason,self.attempted_submissions)
