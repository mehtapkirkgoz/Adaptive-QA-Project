"""Resolve secret references without storing values in project configuration."""

import os
import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SecretValue:
    value: str = field(repr=False)

    def __str__(self) -> str:
        return "[REDACTED]"


@dataclass(frozen=True)
class SecretReference:
    environment_variable: str

    def __post_init__(self) -> None:
        if not isinstance(self.environment_variable, str):
            raise ValueError(
                "environment_variable must be a string."
            )

        if not re.fullmatch(
            r"[A-Z_][A-Z0-9_]*",
            self.environment_variable,
        ):
            raise ValueError(
                "environment_variable must be a valid uppercase variable name."
            )

    def resolve(self) -> SecretValue:
        """Read the secret from the current process environment."""
        value = os.environ.get(self.environment_variable)

        if value is None or not value.strip():
            raise ValueError(
                f"Required secret is missing: {self.environment_variable}"
            )

        return SecretValue(value=value)