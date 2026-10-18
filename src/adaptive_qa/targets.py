"""Combine project authorization and destination validation."""

import socket
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlsplit

from adaptive_qa.config import ProjectConfig, extract_hostname
from adaptive_qa.policy import DestinationPolicy, validate_public_ip


Resolver = Callable[[str, int], tuple[str, ...]]


def resolve_addresses(hostname: str, port: int) -> tuple[str, ...]:
    """Resolve a hostname without opening an application connection."""
    try:
        records = socket.getaddrinfo(
            hostname,
            port,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
        )
    except OSError as error:
        raise ValueError("Destination DNS resolution failed.") from error

    return tuple(sorted({record[4][0] for record in records}))


@dataclass(frozen=True)
class ValidatedTarget:
    hostname: str
    port: int
    addresses: tuple[str, ...]


def validate_target(
    url: str,
    project: ProjectConfig,
    policy: DestinationPolicy,
    *,
    resolver: Resolver = resolve_addresses,
) -> ValidatedTarget:
    """Authorize a URL and validate all resolved destination addresses."""
    policy.validate_url(url)

    if not project.is_url_allowed(url):
        raise ValueError("Destination hostname is not authorized.")

    hostname = extract_hostname(url)
    parsed = urlsplit(url)
    default_port = 443 if parsed.scheme == "https" else 80
    port = parsed.port if parsed.port is not None else default_port

    addresses = resolver(hostname, port)

    if not isinstance(addresses, tuple) or not addresses:
        raise ValueError("Resolver must return a non-empty tuple.")

    for address in addresses:
        validate_public_ip(address)

    return ValidatedTarget(
        hostname=hostname,
        port=port,
        addresses=tuple(sorted(set(addresses))),
    )