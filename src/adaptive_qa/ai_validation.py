"""Structural input minimization and strict validation of untrusted AI JSON."""

from dataclasses import dataclass
import json

from adaptive_qa.ai_models import AiAdvice, AiBudget, ElementAdvice, FeatureAdvice, WebsiteKind
from adaptive_qa.api_models import parse_api_json
from adaptive_qa.discovery import PageSnapshot
from adaptive_qa.models import FeatureStatus


# Unknown page text is omitted rather than guessed to be free of secrets.
SAFE_NAMES = frozenset(('login', 'log in', 'sign in', 'giriş yap', 'oturum aç',
    'search', 'search products', 'ara', 'ürün ara', 'register', 'sign up',
    'create account', 'kayıt ol', 'üye ol', 'username', 'email', 'password',
    'kullanıcı adı', 'e-posta', 'şifre', 'add to cart', 'sepete ekle', 'checkout'))
SAFE_TYPES = frozenset(('text', 'email', 'password', 'search', 'checkbox', 'radio',
                        'number', 'tel', 'url', 'submit', 'button'))
SAFE_AUTOCOMPLETE = frozenset(('username', 'email', 'current-password', 'new-password'))


@dataclass(frozen=True)
class ReducedAiInput:
    payload: str
    evidence_ids: tuple[str, ...]
    candidate_ids: tuple[str, ...]
    collection_complete: bool


def _safe_name(value):
    normalized = ' '.join(value.casefold().split())
    return normalized if normalized in SAFE_NAMES else ''


def reduce_ai_input(page: PageSnapshot, budget: AiBudget) -> ReducedAiInput:
    """Omit URLs, identifiers, raw text, links, values, and commerce names."""
    if not isinstance(page, PageSnapshot) or not isinstance(budget, AiBudget):
        raise ValueError('Typed page and AI budget are required.')
    evidence, candidates, forms, commerce = [], [], [], []
    truncated = len(page.forms) > 20 or len(page.commerce) > 20
    for index, form in enumerate(page.forms[:20]):
        if not form.visible:
            continue
        reference = f'form_{index}'
        evidence.append(reference)
        fields, buttons = [], []
        truncated |= len(form.fields) > 30 or len(form.buttons) > 20
        for field_index, item in enumerate(form.fields[:30]):
            if not item.visible:
                continue
            candidate = f'field_{index}_{field_index}'
            candidates.append(candidate)
            fields.append({'id': candidate,
                'type': item.input_type if item.input_type in SAFE_TYPES else 'other',
                'label': _safe_name(item.label),
                'autocomplete': item.autocomplete if item.autocomplete in SAFE_AUTOCOMPLETE else ''})
        for button_index, text in enumerate(form.buttons[:20]):
            candidate = f'button_{index}_{button_index}'
            candidates.append(candidate)
            buttons.append({'id': candidate, 'name': _safe_name(text)})
        forms.append({'id': reference, 'fields': fields, 'buttons': buttons})
    for index, item in enumerate(page.commerce[:20]):
        if not item.visible:
            continue
        reference = f'commerce_{index}'
        evidence.append(reference)
        commerce.append({'id': reference, 'kind': item.kind, 'has_price': item.has_price,
            'has_currency': item.has_currency, 'has_items': item.has_items,
            'has_quantity': item.has_quantity, 'empty': item.empty,
            'actions': [_safe_name(value) for value in item.actions[:20]]})
        truncated |= len(item.actions) > 20
    complete = page.collection_complete and not truncated
    payload = json.dumps({'schema_version': 1, 'untrusted_page_data': {
        'collection_complete': complete, 'forms': forms, 'commerce': commerce}}, separators=(',', ':'))
    if len(payload.encode('utf-8')) > budget.max_input_bytes:
        raise ValueError('Reduced AI input exceeds the configured byte limit.')
    return ReducedAiInput(payload, tuple(evidence), tuple(candidates), complete)


def _keys(value, expected):
    if type(value) is not dict or set(value) != set(expected):
        raise ValueError('AI response objects must match the exact supported schema.')


def decode_ai_advice(text: str, reduced: ReducedAiInput, logical_names: tuple[str, ...],
                     budget: AiBudget) -> AiAdvice:
    """Reject extra fields, duplicate keys, unknown references, and false absence."""
    try:
        if (not isinstance(text, str) or not isinstance(reduced, ReducedAiInput)
                or not isinstance(budget, AiBudget)
                or not isinstance(logical_names, tuple)
                or any(not isinstance(name, str) for name in logical_names)
                or len(set(logical_names)) != len(logical_names)
                or len(text.encode('utf-8')) > budget.max_output_bytes):
            raise ValueError()
        raw = parse_api_json(text)
        _keys(raw, ('website_kind', 'confidence', 'features', 'elements'))
        if type(raw['features']) is not list or len(raw['features']) > 7:
            raise ValueError()
        if type(raw['elements']) is not list or len(raw['elements']) > 50:
            raise ValueError()
        features, elements = [], []
        for item in raw['features']:
            _keys(item, ('feature', 'status', 'confidence', 'evidence_ids'))
            if type(item['evidence_ids']) is not list:
                raise ValueError()
            feature = FeatureAdvice(item['feature'], FeatureStatus(item['status']),
                                    item['confidence'], tuple(item['evidence_ids']))
            if not set(feature.evidence_ids) <= set(reduced.evidence_ids):
                raise ValueError()
            if feature.status == FeatureStatus.ABSENT and not reduced.collection_complete:
                raise ValueError()
            features.append(feature)
        for item in raw['elements']:
            _keys(item, ('logical_name', 'candidate_id', 'confidence'))
            element = ElementAdvice(**item)
            if element.logical_name not in logical_names or element.candidate_id not in reduced.candidate_ids:
                raise ValueError()
            elements.append(element)
        return AiAdvice(WebsiteKind(raw['website_kind']), raw['confidence'], tuple(features), tuple(elements))
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        raise ValueError('AI response failed schema or collected-reference validation.') from None
