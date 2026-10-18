"""Destination policies for test execution."""

from dataclasses import dataclass
from urllib.parse import urlsplit

from adaptive_qa.config import extract_hostname


@dataclass(frozen=True)
class DestinationPolicy:
    allowed_schemes: tuple[str, ...] = ("https",)
    allowed_ports: tuple[int, ...] = (443,)

    def __post_init__(self) -> None:
        if (
            not isinstance(self.allowed_schemes, tuple)
            or not self.allowed_schemes
        ):
            raise ValueError(
                "allowed_schemes must be a non-empty tuple."
            )

        for scheme in self.allowed_schemes:
            if scheme not in ("http", "https"):
                raise ValueError(
                    "allowed_schemes must contain only http or https."
                )

        if (
            not isinstance(self.allowed_ports, tuple)
            or not self.allowed_ports
        ):
            raise ValueError(
                "allowed_ports must be a non-empty tuple."
            )

        for port in self.allowed_ports:
            if (
                isinstance(port, bool)
                or not isinstance(port, int)
                or not 1 <= port <= 65535
            ):
                raise ValueError(
                    "allowed_ports must contain integers from 1 to 65535."
                )

    def validate_url(self, url: str) -> None:
        """Validate URL syntax, scheme, and effective port."""
        extract_hostname(url)
        parsed = urlsplit(url)

        if parsed.scheme not in self.allowed_schemes:
            raise ValueError("URL scheme is not allowed.")

        default_port = 443 if parsed.scheme == "https" else 80
        effective_port = (
            parsed.port if parsed.port is not None else default_port
        )

        if effective_port not in self.allowed_ports:
            raise ValueError("URL port is not allowed.")