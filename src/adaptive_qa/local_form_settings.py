"""Syntax-only reusable local form settings; no input values or execution authority."""
from adaptive_qa.element_models import ElementMapping,LocatorSpec,LocatorStrategy
from adaptive_qa.interactive_contracts import FormOperation,InteractiveFormContract
from adaptive_qa.local_form_binding import decode_local_binding,encode_local_binding
from adaptive_qa.secrets import SecretReference


def validate_saved_local_binding(raw,project,config):
    required={'operation','document_url','endpoint_url','field_names','accepted','rejected'}
    if not isinstance(raw,dict) or set(raw)!=required:raise ValueError('Exact reusable local binding fields are required.')
    operation=FormOperation(raw['operation'])
    slots=('login_username','login_password') if operation==FormOperation.LOGIN else ('search_query',)
    from adaptive_qa.project_settings import reference_name
    references=tuple(SecretReference(reference_name(project.owner_id,project.project_id,slot)) for slot in slots)
    # This placeholder validates metadata only. The operator must supply a real
    # explicit completion mapping during review; it never becomes a queued contract.
    form=InteractiveFormContract(project.project_id,'0'*64,operation,references,
        ElementMapping('login.accepted' if operation==FormOperation.LOGIN else 'search.results',
            (LocatorSpec(LocatorStrategy.TEST_ID,'review-required'),)))
    binding=decode_local_binding({key:value for key,value in raw.items() if key!='operation'},form)
    if binding.document_url!=config.base_url or config.allowed_hosts!=('127.0.0.1',):
        raise ValueError('Reusable local settings must match the exact owned project document.')
    import json
    return {'operation':operation.value,**json.loads(json.dumps(encode_local_binding(binding)))}
