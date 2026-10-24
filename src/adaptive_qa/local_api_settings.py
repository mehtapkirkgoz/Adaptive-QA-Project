"""Saved explicit read-only API metadata; no input values or execution authority."""
import re
from adaptive_qa.api_models import ApiCase, ApiRequest, JsonCheck, JsonOperator
from adaptive_qa.local_api_review import review_local_api
from adaptive_qa.models import TestCase, TestType


def saved_api_case(data, project):
    fields = {'path', 'expected_status', 'json_field', 'expected_boolean'}
    if not isinstance(data, dict) or set(data) != fields:
        raise ValueError('Exact read-only local API binding fields are required.')
    if (not isinstance(data['path'], str) or len(data['path']) > 256
            or type(data['expected_status']) is not int
            or not (200 <= data['expected_status'] <= 299 or 400 <= data['expected_status'] <= 499)
            or not isinstance(data['json_field'], str)
            or not re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,39}', data['json_field'])
            or type(data['expected_boolean']) is not bool):
        raise ValueError('Bounded API path, status and boolean assertion are required.')
    case = ApiCase(TestCase('LOCAL-API-READ', 'Saved explicit API response', TestType.API,
        ('api',), ('Read the explicitly configured endpoint',), 'Match the saved status and boolean assertion'),
        ApiRequest(data['path']), data['expected_status'],
        (JsonCheck((data['json_field'],), JsonOperator.EQUALS, data['expected_boolean']),))
    review_local_api(project, case)  # Validate the owned origin; never execute.
    return case


def validate_saved_api_binding(data, project):
    saved_api_case(data, project)
    return dict(data)
