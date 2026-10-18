"""Tests for combined target authorization."""

import unittest
from unittest.mock import Mock

from adaptive_qa.config import ProjectConfig
from adaptive_qa.policy import DestinationPolicy
from adaptive_qa.targets import validate_target


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


if __name__ == "__main__":
    unittest.main()