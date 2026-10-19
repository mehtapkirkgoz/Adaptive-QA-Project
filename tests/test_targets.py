"""Tests for combined target authorization."""

import socket
import unittest
from unittest.mock import Mock, patch

from adaptive_qa.config import ProjectConfig
from adaptive_qa.policy import DestinationPolicy
from adaptive_qa.targets import (
    resolve_addresses,
    validate_local_sample_target,
    validate_target,
)


class TargetValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.project = ProjectConfig(
            project_id="demo",
            name="Demo Project",
            base_url="https://example.com",
            allowed_hosts=("example.com",),
        )
        self.policy = DestinationPolicy()

    def test_public_target_is_accepted(self) -> None:
        resolver = Mock(return_value=("8.8.8.8",))

        target = validate_target(
            "https://example.com/login",
            self.project,
            self.policy,
            resolver=resolver,
        )

        self.assertEqual(target.hostname, "example.com")
        self.assertEqual(target.port, 443)
        self.assertEqual(target.addresses, ("8.8.8.8",))
        resolver.assert_called_once_with("example.com", 443)

    def test_unauthorized_host_is_rejected_before_dns(self) -> None:
        resolver = Mock()

        with self.assertRaisesRegex(
            ValueError,
            "Destination hostname is not authorized",
        ):
            validate_target(
                "https://other.example",
                self.project,
                self.policy,
                resolver=resolver,
            )

        resolver.assert_not_called()

    def test_disallowed_port_is_rejected_before_dns(self) -> None:
        resolver = Mock()

        with self.assertRaisesRegex(
            ValueError,
            "URL port is not allowed",
        ):
            validate_target(
                "https://example.com:8443",
                self.project,
                self.policy,
                resolver=resolver,
            )

        resolver.assert_not_called()

    def test_mixed_public_and_private_addresses_are_rejected(self) -> None:
        resolver = Mock(return_value=("8.8.8.8", "127.0.0.1"))

        with self.assertRaisesRegex(
            ValueError,
            "IP address is not an allowed public destination",
        ):
            validate_target(
                "https://example.com",
                self.project,
                self.policy,
                resolver=resolver,
            )

    def test_empty_dns_result_is_rejected(self) -> None:
        resolver = Mock(return_value=())

        with self.assertRaisesRegex(
            ValueError,
            "Resolver must return a non-empty tuple",
        ):
            validate_target(
                "https://example.com",
                self.project,
                self.policy,
                resolver=resolver,
            )


class DNSResolutionTests(unittest.TestCase):
    @patch("adaptive_qa.targets.socket.getaddrinfo")
    def test_ipv4_and_ipv6_addresses_are_returned(self, lookup: Mock) -> None:
        lookup.return_value = [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("8.8.8.8", 443),
            ),
            (
                socket.AF_INET6,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("2606:4700:4700::1111", 443, 0, 0),
            ),
        ]

        addresses = resolve_addresses("example.com", 443)

        self.assertEqual(
            set(addresses),
            {"8.8.8.8", "2606:4700:4700::1111"},
        )
        lookup.assert_called_once_with(
            "example.com",
            443,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
        )

    @patch("adaptive_qa.targets.socket.getaddrinfo")
    def test_duplicate_addresses_are_removed(self, lookup: Mock) -> None:
        record = (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("8.8.8.8", 443),
        )
        lookup.return_value = [record, record]

        self.assertEqual(
            resolve_addresses("example.com", 443),
            ("8.8.8.8",),
        )

    @patch("adaptive_qa.targets.socket.getaddrinfo")
    def test_dns_failure_is_reported(self, lookup: Mock) -> None:
        lookup.side_effect = socket.gaierror("Simulated DNS failure")

        with self.assertRaisesRegex(
            ValueError,
            "Destination DNS resolution failed",
        ):
            resolve_addresses("example.com", 443)



class LocalSampleTargetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.project = ProjectConfig(
            project_id="local-demo",
            name="Local Sample Application",
            base_url="http://127.0.0.1:8000",
            allowed_hosts=("127.0.0.1",),
        )

    def test_local_sample_path_is_accepted(self) -> None:
        target = validate_local_sample_target(
            "http://127.0.0.1:8000/login",
            self.project,
        )

        self.assertEqual(target.hostname, "127.0.0.1")
        self.assertEqual(target.port, 8000)
        self.assertEqual(target.addresses, ("127.0.0.1",))

    def test_other_hosts_are_rejected(self) -> None:
        for hostname in ("localhost", "127.0.0.2", "example.com"):
            with self.subTest(hostname=hostname):
                with self.assertRaisesRegex(
                    ValueError,
                    "Local sample destination must use 127.0.0.1",
                ):
                    validate_local_sample_target(
                        f"http://{hostname}:8000",
                        self.project,
                    )

    def test_other_ports_are_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "URL port is not allowed",
        ):
            validate_local_sample_target(
                "http://127.0.0.1:9000",
                self.project,
            )

    def test_https_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "URL scheme is not allowed",
        ):
            validate_local_sample_target(
                "https://127.0.0.1:8000",
                self.project,
            )

    def test_project_authorization_is_required(self) -> None:
        other_project = ProjectConfig(
            project_id="public-demo",
            name="Public Demo",
            base_url="https://example.com",
            allowed_hosts=("example.com",),
        )

        with self.assertRaisesRegex(
            ValueError,
            "Destination hostname is not authorized",
        ):
            validate_local_sample_target(
                "http://127.0.0.1:8000",
                other_project,
            )


if __name__ == "__main__":
    unittest.main()