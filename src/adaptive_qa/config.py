"""Project configuration and target authorization."""

import re
from ipaddress import ip_address
from dataclasses import dataclass
from urllib.parse import urlsplit


def extract_hostname(url: str) -> str:
    """Extract a normalized hostname from an HTTP or HTTPS URL."""
    if not isinstance(url, str) or not url.strip():
        raise ValueError("url must be a non-empty string.")

    if any(character.isspace() for character in url):
        raise ValueError("url must not contain whitespace.")

    if "\\" in url or any(ord(character) < 32 or ord(character) == 127 for character in url):
        raise ValueError("url must not contain backslashes or control characters.")

    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        parsed.port
    except ValueError as error:
        raise ValueError("url is invalid.") from error

    if parsed.scheme not in ("http", "https"):
        raise ValueError("url must use HTTP or HTTPS.")

    if not hostname:
        raise ValueError("url must include a hostname.")

    if parsed.username is not None or parsed.password is not None:
        raise ValueError("url must not contain credentials.")

    if not hostname.isascii() or "%" in hostname or hostname.endswith("."):
        raise ValueError("url must use an unambiguous ASCII hostname.")
    try:
        ip_address(hostname)
    except ValueError:
        labels = hostname.split(".")
        if len(hostname) > 253 or any(
            not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
            for label in labels
        ):
            raise ValueError("url hostname is invalid.")
    return hostname.lower()


@dataclass(frozen=True)
class ProjectConfig:
    project_id: str
    name: str
    base_url: str
    allowed_hosts: tuple[str, ...]
    allow_data_changes: bool = False

    def __post_init__(self) -> None:
        for field_name, value in (
            ("project_id", self.project_id),
            ("name", self.name),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"{field_name} must be a non-empty string."
                )

        if not isinstance(self.allowed_hosts, tuple) or not self.allowed_hosts:
            raise ValueError("allowed_hosts must be a non-empty tuple.")

        for host in self.allowed_hosts:
            if not isinstance(host, str) or not host:
                raise ValueError(
                    "allowed_hosts must contain non-empty strings."
                )

            if any(character.isspace() for character in host):
                raise ValueError("Allowed hosts must not contain whitespace.")

            if any(character in host for character in "/\\:@?#*"):
                raise ValueError(
                    "Allowed hosts must be hostnames without ports or wildcards."
                )

            if host != host.lower():
                raise ValueError("Allowed hosts must be lowercase.")

        if not isinstance(self.allow_data_changes, bool):
            raise ValueError("allow_data_changes must be a bool.")

        if not self.is_url_allowed(self.base_url):
            raise ValueError("base_url must match an allowed host.")

    def is_url_allowed(self, url: str) -> bool:
        """Check whether a URL matches an explicitly allowed hostname."""
        return extract_hostname(url) in self.allowed_hosts