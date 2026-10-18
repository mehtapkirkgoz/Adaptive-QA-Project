"""Shared models for test definitions and execution states."""

from dataclasses import dataclass
from enum import StrEnum


class TestType(StrEnum):
    UI = "ui"
    API = "api"
    DATABASE = "database"


class TestStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    ERROR = "error"


class FeatureStatus(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class TestCase:
    case_id: str
    name: str
    test_type: TestType
    required_features: tuple[str, ...]
    steps: tuple[str, ...]
    expected_result: str
    changes_data: bool = False

    def __post_init__(self) -> None:
        required_texts = {
            "case_id": self.case_id,
            "name": self.name,
            "expected_result": self.expected_result,
        }

        for field_name, value in required_texts.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"{field_name} must be a non-empty string."
                )

        if not isinstance(self.test_type, TestType):
            raise ValueError("test_type must be a TestType value.")

        for field_name, values in (
            ("required_features", self.required_features),
            ("steps", self.steps),
        ):
            if not isinstance(values, tuple):
                raise ValueError(f"{field_name} must be a tuple.")

            if any(
                not isinstance(value, str) or not value.strip()
                for value in values
            ):
                raise ValueError(
                    f"{field_name} must contain only non-empty strings."
                )

        if not self.steps:
            raise ValueError("A test case must contain at least one step.")

        if not isinstance(self.changes_data, bool):
            raise ValueError("changes_data must be a bool.")