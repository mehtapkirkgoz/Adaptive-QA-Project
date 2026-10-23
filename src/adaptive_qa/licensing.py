"""Offline signed entitlements; no target data, networking or issuer private keys."""

import base64
import binascii
from dataclasses import dataclass
import json
import math
import re
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


class LicenseError(ValueError):
    """Untrusted license input never appears in error messages."""


@dataclass(frozen=True)
class LicenseClaims:
    license_id: str
    customer_id: str
    issued_at: int
    not_before: int
    expires_at: int
    max_projects: int | None
    max_concurrent_runs: int
    product: str = 'adaptive-qa-local'
    edition: str = 'professional'
    schema_version: int = 1

    def __post_init__(self):
        if (type(self.schema_version) is not int or self.schema_version != 1
                or self.product != 'adaptive-qa-local' or self.edition != 'professional'
                or any(not isinstance(value, str) or not re.fullmatch('[0-9a-f]{32}', value)
                       for value in (self.license_id, self.customer_id))
                or any(type(value) is not int or not 0 <= value <= 4102444800
                       for value in (self.issued_at, self.not_before, self.expires_at))
                or not self.issued_at <= self.not_before < self.expires_at
                or (self.max_projects is not None and (type(self.max_projects) is not int or not 1 <= self.max_projects <= 10000))
                or type(self.max_concurrent_runs) is not int or not 1 <= self.max_concurrent_runs <= 4):
            raise LicenseError('Invalid license claims.')


def license_message(key_id, payload):
    if not isinstance(key_id, str) or not re.fullmatch('[A-Za-z0-9_-]{1,64}', key_id):
        raise LicenseError('Invalid license envelope.')
    return b'adaptive-qa-license-v1\0'+key_id.encode('ascii')+b'\0'+json.dumps(
        payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('utf-8')


def verify_license(document, trusted_keys, *, now=None):
    """Only externally supplied trusted Ed25519 public keys grant entitlements."""
    try:
        if not isinstance(document, bytes) or not 1 <= len(document) <= 8192:
            raise ValueError()
        if not isinstance(trusted_keys, dict) or not 1 <= len(trusted_keys) <= 10:
            raise ValueError()
        current = time.time() if now is None else now
        if isinstance(current, bool) or not isinstance(current, (int, float)) or not 0 <= current <= 4102444800 or not math.isfinite(current):
            raise ValueError()
        def unique(pairs):
            value = {}
            for key, item in pairs:
                if key in value:
                    raise ValueError()
                value[key] = item
            return value
        def invalid_constant(value):
            raise ValueError()
        envelope = json.loads(document.decode('utf-8'), object_pairs_hook=unique, parse_constant=invalid_constant)
        if not isinstance(envelope, dict) or set(envelope) != {'key_id', 'payload', 'signature'}:
            raise ValueError()
        key_id, payload, encoded = envelope['key_id'], envelope['payload'], envelope['signature']
        if not isinstance(key_id, str) or not isinstance(payload, dict) or not isinstance(encoded, str):
            raise ValueError()
        if set(payload) != set(LicenseClaims.__dataclass_fields__):
            raise ValueError()
        raw_key = trusted_keys.get(key_id)
        if not isinstance(raw_key, bytes) or len(raw_key) != 32:
            raise ValueError()
        if not re.fullmatch('[A-Za-z0-9_-]{86}', encoded):
            raise ValueError()
        signature = base64.b64decode(encoded+'==', altchars=b'-_', validate=True)
        if base64.urlsafe_b64encode(signature).rstrip(b'=').decode('ascii') != encoded:
            raise ValueError()
        Ed25519PublicKey.from_public_bytes(raw_key).verify(signature, license_message(key_id, payload))
        claims = LicenseClaims(**payload)
        if not claims.issued_at <= current or not claims.not_before <= current < claims.expires_at:
            raise ValueError()
        return claims
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError, binascii.Error, InvalidSignature):
        raise LicenseError('License verification failed.') from None
