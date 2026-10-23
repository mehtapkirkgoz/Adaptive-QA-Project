"""Non-executing contracts for future controlled form submission workers."""
from dataclasses import asdict, dataclass
from enum import StrEnum
import hashlib
import json
import re

from adaptive_qa.config import ProjectConfig
from adaptive_qa.element_models import ElementMapping
from adaptive_qa.project_store import _id
from adaptive_qa.secrets import SecretReference


class FormOperation(StrEnum):
    LOGIN = 'login'
    SEARCH = 'search'


@dataclass(frozen=True)
class InteractiveFormContract:
    """References and a fixed postcondition, never plaintext inputs or execution authority."""
    project_id: str
    configuration_fingerprint: str
    operation: FormOperation
    inputs: tuple[SecretReference, ...]
    completion: ElementMapping
    timeout_seconds: int = 15

    def __post_init__(self):
        _id(self.project_id)
        if (not isinstance(self.configuration_fingerprint,str)
                or not re.fullmatch('[0-9a-f]{64}',self.configuration_fingerprint)
                or not isinstance(self.operation,FormOperation)):
            raise ValueError('A typed operation and exact saved-configuration fingerprint are required.')
        count = 2 if self.operation == FormOperation.LOGIN else 1
        if (not isinstance(self.inputs,tuple) or len(self.inputs)!=count
                or any(not isinstance(reference,SecretReference) or len(reference.environment_variable)>160 for reference in self.inputs)
                or len({reference.environment_variable for reference in self.inputs})!=count):
            raise ValueError('Distinct typed input references are required; plaintext values are not accepted.')
        if (not isinstance(self.completion,ElementMapping)
                or self.completion.logical_name not in (
                    ('login.accepted','login.rejected') if self.operation==FormOperation.LOGIN else ('search.results','search.empty'))
                or type(self.timeout_seconds) is not int or not 5<=self.timeout_seconds<=30):
            raise ValueError('An explicit operation-specific postcondition and bounded timeout are required.')

    @property
    def changes_data(self):
        return True

    @property
    def max_submissions(self):
        return 1

    def validate_project(self, config, *, current_fingerprint):
        if (not isinstance(config,ProjectConfig) or config.project_id!=self.project_id
                or config.allow_data_changes is not True
                or current_fingerprint!=self.configuration_fingerprint):
            raise ValueError('Interactive submission requires the matching saved project and data-change permission.')
        # This validation does not perform DNS/target guards, resolve an input or execute a plan.

    def fingerprint(self):
        payload = {**asdict(self),'changes_data':True,'max_submissions':1,'completion_must_be_absent_before_submit':True}
        return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
