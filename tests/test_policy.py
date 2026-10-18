"""Tests for destination scheme and port policies."""

import unittest

from adaptive_qa.policy import DestinationPolicy


class DestinationPolicyTests(unittest.TestCase):
    def test_default_policy_accepts_https(self) -> None:
        DestinationPolicy().validate_url("https://example.com")

    def test_default_policy_accepts_explicit_https_port(self) -> None:
        DestinationPolicy().validate_url("https://example.com:443")

    def test_default_policy_rejects_http(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "URL scheme is not allowed",
        ):
            DestinationPolicy().validate_url("http://example.com")

    def test_default_policy_rejects_unlisted_port(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "URL port is not allowed",
        ):
            DestinationPolicy().validate_url("https://example.com:8443")

    def test_custom_policy_accepts_http_default_port(self) -> None:
        policy = DestinationPolicy(
            allowed_schemes=("http",),
            allowed_ports=(80,),
        )

        policy.validate_url("http://example.com")

    def test_custom_policy_accepts_explicit_port(self) -> None:
        policy = DestinationPolicy(
            allowed_schemes=("http",),
            allowed_ports=(8000,),
        )

        policy.validate_url("http://example.com:8000")

    def test_port_zero_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "URL port is not allowed",
        ):
            DestinationPolicy().validate_url("https://example.com:0")

    def test_invalid_scheme_configuration_is_rejected(self) -> None:
        for schemes in ((), ["https"], ("ftp",)):
            with self.subTest(schemes=schemes):
                with self.assertRaises(ValueError):
                    DestinationPolicy(allowed_schemes=schemes)

    def test_invalid_port_configuration_is_rejected(self) -> None:
        for ports in ((), [443], (True,), (0,), (65536,), ("443",)):
            with self.subTest(ports=ports):
                with self.assertRaises(ValueError):
                    DestinationPolicy(allowed_ports=ports)

    def test_invalid_target_urls_are_rejected(self) -> None:
        urls = (
            "",
            "https://",
            "https://example.com:invalid",
            "https://user:password@example.com",
            "https://example .com",
        )

        for url in urls:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    DestinationPolicy().validate_url(url)


if __name__ == "__main__":
    unittest.main()