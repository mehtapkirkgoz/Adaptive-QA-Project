"""Tampering, issuer trust, bounded parsing and exact expiry for offline claims."""
import base64
from dataclasses import asdict
import json
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from adaptive_qa.licensing import LicenseClaims, LicenseError, license_message, verify_license


class LicensingTests(unittest.TestCase):
    def setUp(self):
        self.private = Ed25519PrivateKey.generate()
        self.keys = {'issuer-1': self.private.public_key().public_bytes_raw()}
        self.claims = LicenseClaims('a'*32, 'b'*32, 100, 100, 200, None, 2)

    def document(self, **changes):
        payload = {**asdict(self.claims), **changes}
        signature = self.private.sign(license_message('issuer-1', payload))
        return json.dumps({'key_id': 'issuer-1', 'payload': payload,
            'signature': base64.urlsafe_b64encode(signature).rstrip(b'=').decode('ascii')}).encode()

    def test_verified_entitlements_need_no_network_or_customer_test_data(self):
        with patch('socket.getaddrinfo', side_effect=AssertionError('No DNS')), \
                patch('socket.socket', side_effect=AssertionError('No network')):
            self.assertEqual(verify_license(self.document(), self.keys, now=150), self.claims)
        self.assertIsNone(self.claims.max_projects)
        self.assertLessEqual(self.claims.max_concurrent_runs, 4)

    def test_tampered_payload_signature_and_issuer_are_rejected(self):
        original = json.loads(self.document())
        for field, value in (('payload', {**original['payload'], 'expires_at': 999}),
                             ('signature', 'A'*86), ('key_id', 'unknown')):
            with self.subTest(field=field), self.assertRaises(LicenseError):
                verify_license(json.dumps({**original, field: value}).encode(), self.keys, now=150)
        other = Ed25519PrivateKey.generate().public_key().public_bytes_raw()
        for keys in ({}, {'issuer-1': other}, {'issuer-1': b'wrong'}):
            with self.assertRaises(LicenseError): verify_license(self.document(), keys, now=150)

    def test_validity_boundaries_do_not_grant_grace_or_future_access(self):
        for now in (99, 200, 201, True, float('nan'), float('inf'), -1, 10**1000):
            with self.subTest(now=now), self.assertRaises(LicenseError):
                verify_license(self.document(), self.keys, now=now)
        self.assertEqual(verify_license(self.document(), self.keys, now=100), self.claims)
        self.assertEqual(verify_license(self.document(), self.keys, now=199.9), self.claims)

    def test_even_signed_malformed_claims_cannot_grant_access(self):
        for changes in ({'schema_version': True}, {'product': 'other'}, {'edition': 'free'},
                        {'max_projects': True}, {'max_projects': 0}, {'max_concurrent_runs': 999},
                        {'not_before': 201}, {'issued_at': True}, {'target_url': 'must-not-be-accepted'}):
            with self.subTest(changes=changes), self.assertRaises(LicenseError):
                verify_license(self.document(**changes), self.keys, now=150)

    def test_ambiguous_oversized_and_untyped_inputs_fail_with_safe_errors(self):
        for raw in (b'{}', b'[]', b'\xff', b'x'*8193, b'{"key_id":"one","key_id":"two"}', 'untyped'):
            with self.subTest(raw=type(raw)), self.assertRaisesRegex(LicenseError, '^License verification failed.$'):
                verify_license(raw, self.keys, now=150)
