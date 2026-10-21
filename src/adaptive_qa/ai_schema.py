"""Shared closed JSON schema for provider-independent QA advice."""

from adaptive_qa.ai_models import FEATURE_NAMES


def _object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}



def advice_json_schema(reduced, logical_names):
    confidence = {'type': 'number', 'minimum': 0, 'maximum': 1}
    feature = _object({'feature': {'type': 'string', 'enum': sorted(FEATURE_NAMES)},
        'status': {'type': 'string', 'enum': ['present', 'unknown'] + (['absent'] if reduced.collection_complete else [])},
        'confidence': confidence,
        'evidence_ids': {'type': 'array', 'minItems': 1, 'maxItems': min(20, max(1, len(reduced.evidence_ids))),
                         'items': {'type': 'string', 'enum': list(reduced.evidence_ids) or ['unavailable']}}})
    element = _object({'logical_name': {'type': 'string', 'enum': list(logical_names) or ['unavailable']},
        'candidate_id': {'type': 'string', 'enum': list(reduced.candidate_ids) or ['unavailable']},
        'confidence': confidence})
    schema = _object({'website_kind': {'type': 'string', 'enum': ['commerce', 'general', 'unknown']},
        'confidence': confidence,
        'features': {'type': 'array', 'maxItems': 7 if reduced.evidence_ids else 0, 'items': feature},
        'elements': {'type': 'array', 'maxItems': 50 if logical_names and reduced.candidate_ids else 0, 'items': element}})
    return schema
