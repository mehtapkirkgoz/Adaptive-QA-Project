"""Validated contracts for deterministic element mappings and match outcomes."""

from dataclasses import dataclass
from enum import StrEnum
import re


class LocatorStrategy(StrEnum):
    ROLE = 'role'
    LABEL = 'label'
    TEST_ID = 'test_id'


class MatchStatus(StrEnum):
    MATCHED = 'matched'
    MISSING = 'missing'
    AMBIGUOUS = 'ambiguous'
    ERROR = 'error'


def _text(value: str, name: str, maximum: int = 160) -> None:
    if (not isinstance(value, str) or not value.strip() or len(value) > maximum
            or any(ord(character) < 32 or ord(character) == 127 for character in value)):
        raise ValueError(f'{name} must be non-empty text of at most {maximum} characters without controls.')


def _logical_name(value: str) -> None:
    _text(value, 'logical_name', 80)
    if not re.fullmatch(r'[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*', value):
        raise ValueError('logical_name must use lowercase dotted identifiers.')


@dataclass(frozen=True)
class LocatorSpec:
    strategy: LocatorStrategy
    value: str
    role: str | None = None

    def __post_init__(self):
        if not isinstance(self.strategy, LocatorStrategy):
            raise ValueError('strategy must be a LocatorStrategy.')
        _text(self.value, 'value')
        if self.strategy == LocatorStrategy.ROLE:
            if self.role not in ('button', 'textbox', 'searchbox', 'link', 'checkbox',
                                 'radio', 'combobox', 'spinbutton', 'form', 'region'):
                raise ValueError('Role locators require a supported accessible role.')
        elif self.role is not None:
            raise ValueError('role is only supported by role locators.')


@dataclass(frozen=True)
class ElementMapping:
    logical_name: str
    locators: tuple[LocatorSpec, ...]
    scope_test_id: str | None = None

    def __post_init__(self):
        _logical_name(self.logical_name)
        if (not isinstance(self.locators, tuple) or not 1 <= len(self.locators) <= 20
                or any(not isinstance(locator, LocatorSpec) for locator in self.locators)):
            raise ValueError('locators must contain between 1 and 20 LocatorSpec instances in a tuple.')
        if len(set(self.locators)) != len(self.locators):
            raise ValueError('Duplicate locator alternatives are not allowed.')
        if self.scope_test_id is not None:
            _text(self.scope_test_id, 'scope_test_id')


@dataclass(frozen=True)
class ProjectElementMappings:
    project_id: str
    mappings: tuple[ElementMapping, ...] = ()

    def __post_init__(self):
        _text(self.project_id, 'project_id', 80)
        if (not isinstance(self.mappings, tuple) or len(self.mappings) > 200
                or any(not isinstance(mapping, ElementMapping) for mapping in self.mappings)):
            raise ValueError('mappings must be a tuple of at most 200 ElementMapping instances.')
        if len({mapping.logical_name for mapping in self.mappings}) != len(self.mappings):
            raise ValueError('Project mapping logical names must be unique.')

    def resolve(self, default: ElementMapping, *, project_id: str) -> ElementMapping:
        """Use an explicit project override as a replacement, not a fallback union."""
        if not isinstance(default, ElementMapping):
            raise ValueError('default must be an ElementMapping.')
        if project_id != self.project_id:
            raise ValueError('Element mappings belong to a different project.')
        return next((mapping for mapping in self.mappings
                     if mapping.logical_name == default.logical_name), default)


@dataclass(frozen=True)
class MatchResult:
    logical_name: str
    status: MatchStatus
    candidate_count: int
    reason: str
    rule_indexes: tuple[int, ...] = ()

    def __post_init__(self):
        _logical_name(self.logical_name)
        if not isinstance(self.status, MatchStatus):
            raise ValueError('status must be a MatchStatus.')
        if type(self.candidate_count) is not int or self.candidate_count < 0:
            raise ValueError('candidate_count must be a non-negative integer.')
        _text(self.reason, 'reason', 500)
        if (not isinstance(self.rule_indexes, tuple)
                or any(type(index) is not int or not 0 <= index < 20 for index in self.rule_indexes)
                or len(set(self.rule_indexes)) != len(self.rule_indexes)):
            raise ValueError('rule_indexes must contain unique integer indexes between 0 and 19.')
        if self.status == MatchStatus.MATCHED:
            valid = self.candidate_count == 1 and bool(self.rule_indexes)
        elif self.status == MatchStatus.AMBIGUOUS:
            valid = self.candidate_count >= 2 and bool(self.rule_indexes)
        else:
            valid = self.candidate_count == 0 and not self.rule_indexes
        if not valid:
            raise ValueError('Match status, candidate count, and rule indexes are inconsistent.')
