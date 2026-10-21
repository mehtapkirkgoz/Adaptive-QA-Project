"""Provider-independent advisory contracts; no model output authorizes execution."""

from dataclasses import dataclass, field
from enum import StrEnum
import math
import re
from typing import Protocol

from adaptive_qa.models import FeatureStatus


FEATURE_NAMES = frozenset(('login', 'search', 'registration', 'product', 'cart', 'forms', 'navigation'))


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,63}', value):
        raise ValueError('AI reference identifiers must be bounded lowercase ASCII names.')


def _confidence(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError('Confidence must be finite and between zero and one.')


class WebsiteKind(StrEnum):
    COMMERCE = 'commerce'
    GENERAL = 'general'
    UNKNOWN = 'unknown'


@dataclass(frozen=True)
class AiBudget:
    max_requests: int = 1
    timeout_seconds: float = 10
    max_input_bytes: int = 16384
    max_output_bytes: int = 8192
    max_cost_microusd: int = 0

    def __post_init__(self):
        for value, maximum in ((self.max_requests, 10), (self.max_input_bytes, 65536),
                               (self.max_output_bytes, 32768)):
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError('AI request and byte budgets must be bounded positive integers.')
        if (type(self.timeout_seconds) not in (int, float) or not math.isfinite(self.timeout_seconds)
                or not 0 < self.timeout_seconds <= 60):
            raise ValueError('AI timeout must be finite and in (0, 60].')
        if type(self.max_cost_microusd) is not int or not 0 <= self.max_cost_microusd <= 1000000:
            raise ValueError('AI cost budget must be a bounded nonnegative integer.')


@dataclass(frozen=True)
class FeatureAdvice:
    feature: str
    status: FeatureStatus
    confidence: float
    evidence_ids: tuple[str, ...]

    def __post_init__(self):
        if (not isinstance(self.feature, str) or self.feature not in FEATURE_NAMES
                or not isinstance(self.status, FeatureStatus)):
            raise ValueError('AI advice must reference a supported feature and typed status.')
        _confidence(self.confidence)
        if not isinstance(self.evidence_ids, tuple) or not 1 <= len(self.evidence_ids) <= 20:
            raise ValueError('Feature advice requires one to twenty evidence references.')
        for value in self.evidence_ids:
            _identifier(value)
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError('Evidence references must be unique.')


@dataclass(frozen=True)
class ElementAdvice:
    logical_name: str
    candidate_id: str
    confidence: float

    def __post_init__(self):
        if not isinstance(self.logical_name, str) or not re.fullmatch(r'[a-z][a-z0-9_.]{0,79}', self.logical_name):
            raise ValueError('Logical element names must be bounded reference names.')
        _identifier(self.candidate_id)
        _confidence(self.confidence)


@dataclass(frozen=True)
class AiAdvice:
    website_kind: WebsiteKind
    confidence: float
    features: tuple[FeatureAdvice, ...] = ()
    elements: tuple[ElementAdvice, ...] = ()
    execution_authorized: bool = field(default=False, init=False)

    def __post_init__(self):
        if not isinstance(self.website_kind, WebsiteKind):
            raise ValueError('website_kind must be a WebsiteKind.')
        _confidence(self.confidence)
        for values, cls, maximum in ((self.features, FeatureAdvice, 7), (self.elements, ElementAdvice, 50)):
            if (not isinstance(values, tuple) or len(values) > maximum
                    or any(not isinstance(value, cls) for value in values)):
                raise ValueError('AI advice collections must contain bounded typed tuples.')
        if len({item.feature for item in self.features}) != len(self.features):
            raise ValueError('Feature advice must have unique feature names.')
        if len({item.logical_name for item in self.elements}) != len(self.elements):
            raise ValueError('Element advice must have unique logical names.')


class AiProvider(Protocol):
    def suggest(self, reduced_input: str, budget: AiBudget) -> str:
        """Return untrusted JSON; the host must validate references and policy."""
        ...
