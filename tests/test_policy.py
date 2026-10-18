"""Tests for destination scheme and port policies."""

import unittest

from adaptive_qa.policy import DestinationPolicy, validate_public_ip


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


class PublicIPAddressTests(unittest.TestCase):
    def test_public_addresses_are_accepted(self) -> None:
        for address in ("8.8.8.8", "2606:4700:4700::1111"):
            with self.subTest(address=address):
                validate_public_ip(address)

    def test_non_public_destinations_are_rejected(self) -> None:
        addresses = (
            "127.0.0.1",
            "10.0.0.1",
            "172.16.0.1",
            "192.168.1.1",
            "169.254.169.254",
            "100.64.0.1",
            "0.0.0.0",
            "224.0.0.1",
            "::1",
            "::",
            "fc00::1",
            "fe80::1",
            "ff02::1",
            "192.0.2.1",
            "2001:db8::1",
        )

        for address in addresses:
            with self.subTest(address=address):
                with self.assertRaisesRegex(
                    ValueError,
                    "IP address is not an allowed public destination",
                ):
                    validate_public_ip(address)

    def test_ipv6_transition_addresses_are_rejected(self) -> None:
        addresses = (
            "::ffff:8.8.8.8",
            "2002:0808:0808::1",
            "2001:0000:4136:e378:8000:63bf:3fff:fdd2",
        )

        for address in addresses:
            with self.subTest(address=address):
                with self.assertRaisesRegex(
                    ValueError,
                    "IPv6 transition addresses are not allowed",
                ):
                    validate_public_ip(address)

    def test_scoped_addresses_are_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Scoped IP addresses are not allowed",
        ):
            validate_public_ip("fe80::1%eth0")

    def test_invalid_addresses_are_rejected(self) -> None:
        for address in ("", None, "example.com", "999.1.1.1"):
            with self.subTest(address=address):
                with self.assertRaises(ValueError):
                    validate_public_ip(address)


if __name__ == "__main__":
    unittest.main()