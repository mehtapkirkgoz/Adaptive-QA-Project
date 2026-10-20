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
    resolver: Resolver | None = None,
) -> ValidatedTarget:
    """Authorize a URL and validate all resolved destination addresses."""
    policy.validate_url(url)

    if not project.is_url_allowed(url):
        raise ValueError("Destination hostname is not authorized.")

    hostname = extract_hostname(url)
    parsed = urlsplit(url)
    default_port = 443 if parsed.scheme == "https" else 80
    port = parsed.port if parsed.port is not None else default_port

    if resolver is None:
        from adaptive_qa.dns_resolver import resolve_with_deadline
        resolver = resolve_with_deadline
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


def validate_local_sample_target(
    url: str,
    project: ProjectConfig,
) -> ValidatedTarget:
    """Validate the fixed local sample destination for development only."""
    policy = DestinationPolicy(
        allowed_schemes=("http",),
        allowed_ports=(8000,),
    )
    policy.validate_url(url)

    hostname = extract_hostname(url)

    if hostname != "127.0.0.1":
        raise ValueError(
            "Local sample destination must use 127.0.0.1."
        )

    if not project.is_url_allowed(url):
        raise ValueError("Destination hostname is not authorized.")

    return ValidatedTarget(
        hostname=hostname,
        port=8000,
        addresses=("127.0.0.1",),
    )