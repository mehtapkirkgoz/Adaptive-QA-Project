"""Shared models for test definitions and execution states."""

from dataclasses import dataclass
from enum import StrEnum
import math


class TestType(StrEnum):
    UI = "ui"
    API = "api"
    DATABASE = "database"


class TestStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
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

@dataclass(frozen=True)
class TestResult:
    case_id: str
    status: TestStatus
    duration_seconds: float
    message: str
    evidence_paths: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.case_id, str) or not self.case_id.strip():
            raise ValueError("case_id must be a non-empty string.")

        if not isinstance(self.status, TestStatus):
            raise ValueError("status must be a TestStatus value.")

        if (
            isinstance(self.duration_seconds, bool)
            or not isinstance(self.duration_seconds, (int, float))
        ):
            raise ValueError("duration_seconds must be a number.")

        if not math.isfinite(self.duration_seconds):
            raise ValueError("duration_seconds must be finite.")

        if self.duration_seconds < 0:
            raise ValueError("duration_seconds must not be negative.")

        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError("message must be a non-empty string.")
        if not isinstance(self.evidence_paths, tuple):
            raise ValueError("evidence_paths must be a tuple.")

        if any(
            not isinstance(path, str) or not path.strip()
            for path in self.evidence_paths
        ):
            raise ValueError(
                "evidence_paths must contain only non-empty strings."
            )
