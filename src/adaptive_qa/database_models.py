"""Non-executing contracts for bounded, read-only SQLite validation."""

from dataclasses import dataclass, field
from enum import StrEnum
import math
import re

from adaptive_qa.config import ProjectConfig
from adaptive_qa.models import TestCase, TestType
from adaptive_qa.secrets import SecretReference


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,63}', value):
        raise ValueError('Identifiers must be bounded lowercase ASCII names.')


def _scalar(value):
    if value is None or type(value) is bool:
        return
    if type(value) is int and -(2**63) <= value < 2**63:
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is str:
        try:
            if len(value.encode('utf-8')) <= 4096:
                return
        except UnicodeError:
            pass
    raise ValueError('Database operands must be bounded finite scalar values.')


@dataclass(frozen=True)
class DatabaseConfiguration:
    project: ProjectConfig
    database_path: SecretReference
    timeout_seconds: float = 5
    max_rows: int = 100
    max_result_bytes: int = 65536

    def __post_init__(self):
        if not isinstance(self.project, ProjectConfig):
            raise ValueError('project must be a ProjectConfig.')
        if not isinstance(self.database_path, SecretReference):
            raise ValueError('database_path must be an environment secret reference.')
        if (type(self.timeout_seconds) not in (int, float)
                or not math.isfinite(self.timeout_seconds)
                or not 0 < self.timeout_seconds <= 10):
            raise ValueError('timeout_seconds must be finite and in (0, 10].')
        for name, value, maximum in (
            ('max_rows', self.max_rows, 1000),
            ('max_result_bytes', self.max_result_bytes, 1048576),
        ):
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError(f'{name} must be a bounded positive integer.')


@dataclass(frozen=True)
class QueryTemplate:
    project_id: str
    template_id: str
    sql: str = field(repr=False)
    parameter_names: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.project_id, str) or not self.project_id.strip():
            raise ValueError('project_id must be non-empty text.')
        _identifier(self.template_id)
        if not isinstance(self.sql, str) or not self.sql.strip() or '\x00' in self.sql:
            raise ValueError('sql must be bounded non-empty text without NUL.')
        try:
            valid = len(self.sql.encode('utf-8')) <= 16384
        except UnicodeError:
            valid = False
        if not valid:
            raise ValueError('sql must be bounded UTF-8 text.')
        if not isinstance(self.parameter_names, tuple) or len(self.parameter_names) > 20:
            raise ValueError('parameter_names must be a tuple of at most 20 names.')
        for name in self.parameter_names:
            _identifier(name)
        if len(set(self.parameter_names)) != len(self.parameter_names):
            raise ValueError('Parameter names must be unique.')


class DatabaseOperator(StrEnum):
    ROW_COUNT = 'row_count'
    CELL_EQUALS = 'cell_equals'


@dataclass(frozen=True)
class DatabaseCheck:
    operator: DatabaseOperator
    expected: object = field(repr=False)
    row: int = 0
    column: int = 0

    def __post_init__(self):
        if not isinstance(self.operator, DatabaseOperator):
            raise ValueError('operator must be a DatabaseOperator.')
        if type(self.row) is not int or not 0 <= self.row < 1000:
            raise ValueError('row must be an integer in [0, 1000).')
        if type(self.column) is not int or not 0 <= self.column < 100:
            raise ValueError('column must be an integer in [0, 100).')
        if self.operator == DatabaseOperator.ROW_COUNT:
            if type(self.expected) is not int or not 0 <= self.expected <= 1000:
                raise ValueError('Expected row count must be an integer in [0, 1000].')
            if self.row != 0 or self.column != 0:
                raise ValueError('Row-count checks cannot select a cell.')
        else:
            _scalar(self.expected)


@dataclass(frozen=True)
class DatabaseCase:
    definition: TestCase
    template: QueryTemplate
    parameters: tuple[tuple[str, object], ...] = field(default=(), repr=False)
    checks: tuple[DatabaseCheck, ...] = ()

    def __post_init__(self):
        if not isinstance(self.definition, TestCase) or self.definition.test_type != TestType.DATABASE:
            raise ValueError('definition must be a database TestCase.')
        if self.definition.changes_data:
            raise ValueError('The database validation adapter supports read-only cases only.')
        if not isinstance(self.template, QueryTemplate):
            raise ValueError('template must be a QueryTemplate.')
        if not isinstance(self.parameters, tuple) or len(self.parameters) > 20:
            raise ValueError('parameters must be a tuple of at most 20 pairs.')
        names = []
        for pair in self.parameters:
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise ValueError('Parameters must be name/value tuples.')
            name, value = pair
            _identifier(name)
            _scalar(value)
            names.append(name)
        if len(set(names)) != len(names) or set(names) != set(self.template.parameter_names):
            raise ValueError('Parameters must match the template names exactly once.')
        if (not isinstance(self.checks, tuple) or not 1 <= len(self.checks) <= 50
                or any(not isinstance(check, DatabaseCheck) for check in self.checks)):
            raise ValueError('checks must contain between 1 and 50 DatabaseCheck values.')
