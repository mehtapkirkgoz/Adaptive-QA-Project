"""Tests for destination pinning, redirect policies, and bounded DNS."""

import subprocess
import unittest
from unittest.mock import Mock, patch

from adaptive_qa.config import ProjectConfig, extract_hostname
from adaptive_qa.dns_resolver import resolve_with_deadline
from adaptive_qa.egress import DestinationGuard, chromium_proxy_options
from adaptive_qa.policy import DestinationPolicy
from adaptive_qa.targets import ValidatedTarget, validate_target


class DestinationGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.project = ProjectConfig("demo", "Demo", "https://example.com", ("example.com",))
        self.guard = DestinationGuard(self.project)

    def test_connection_timeout_is_bounded_before_socket_creation(self):
        target = ValidatedTarget('example.com', 443, ('8.8.8.8',))
        with patch('adaptive_qa.egress.socket.socket') as create:
            for timeout in (True, 0, float('nan'), 6):
                with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                    self.guard.connect(target, timeout_seconds=timeout)
            create.assert_not_called()

    def test_checked_connection_uses_requested_short_timeout(self):
        target = ValidatedTarget('example.com', 443, ('8.8.8.8',))
        with patch('adaptive_qa.egress.socket.socket') as create:
            create.return_value.getpeername.return_value = ('8.8.8.8', 443)
            self.guard.connect(target, timeout_seconds=0.25)
            create.return_value.settimeout.assert_called_once_with(0.25)

    @patch("adaptive_qa.egress.resolve_with_deadline", return_value=("8.8.8.8",))
    def test_public_target_is_validated(self, resolve) -> None:
        target = self.guard.authorize("https://example.com/path")
        self.assertEqual(target.addresses, ("8.8.8.8",))
        resolve.assert_called_once_with("example.com", 443)

    @patch("adaptive_qa.egress.resolve_with_deadline")
    def test_unauthorized_host_is_rejected_before_dns(self, resolve) -> None:
        with self.assertRaises(ValueError):
            self.guard.authorize("https://metadata.example")
        resolve.assert_not_called()

    @patch("adaptive_qa.egress.resolve_with_deadline", return_value=("8.8.8.8", "127.0.0.1"))
    def test_mixed_public_and_private_dns_answer_is_rejected(self, resolve) -> None:
        with self.assertRaises(ValueError):
            self.guard.authorize("https://example.com")

    @patch("adaptive_qa.egress.resolve_with_deadline")
    def test_rebinding_is_rejected_on_subsequent_authorization(self, resolve) -> None:
        resolve.side_effect = [("8.8.8.8",), ("169.254.169.254",)]
        self.guard.authorize("https://example.com")
        with self.assertRaises(ValueError):
            self.guard.authorize("https://example.com/next")

    @patch("adaptive_qa.egress.socket.socket")
    def test_connect_uses_checked_numeric_address_without_hostname_lookup(self, create) -> None:
        connection = create.return_value
        connection.getpeername.return_value = ("8.8.8.8", 443)
        target = ValidatedTarget("example.com", 443, ("8.8.8.8",))
        self.assertIs(self.guard.connect(target), connection)
        connection.connect.assert_called_once_with(("8.8.8.8", 443))

    @patch("adaptive_qa.egress.socket.socket")
    def test_unexpected_connected_peer_is_rejected(self, create) -> None:
        create.return_value.getpeername.return_value = ("127.0.0.1", 443)
        with self.assertRaises(ValueError):
            self.guard.connect(ValidatedTarget("example.com", 443, ("8.8.8.8",)))
        create.return_value.close.assert_called_once()

    def test_private_ip_is_rejected_before_socket_creation(self) -> None:
        with patch("adaptive_qa.egress.socket.socket") as create:
            with self.assertRaises(ValueError):
                self.guard.connect(ValidatedTarget("example.com", 443, ("127.0.0.1",)))
            create.assert_not_called()

    def test_local_policy_does_not_resolve_dns_or_allow_other_ports(self) -> None:
        project = ProjectConfig("local", "Local", "http://127.0.0.1:8000", ("127.0.0.1",))
        guard = DestinationGuard(project, local_sample=True)
        with patch("adaptive_qa.egress.resolve_with_deadline") as resolve:
            guard.authorize(project.base_url)
            with self.assertRaises(ValueError):
                guard.authorize("http://127.0.0.1:8001")
            resolve.assert_not_called()

    @patch("adaptive_qa.egress.resolve_with_deadline", return_value=("8.8.8.8",))
    def test_relative_redirect_is_validated_and_budget_is_bounded(self, resolve) -> None:
        self.guard.redirect("https://example.com/start", "/next")
        for _ in range(9):
            self.guard.redirect("https://example.com/start", "/next")
        with self.assertRaisesRegex(ValueError, "Redirect budget"):
            self.guard.redirect("https://example.com/start", "/next")

    def test_redirect_to_unauthorized_target_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.guard.redirect("https://example.com", "http://169.254.169.254/latest")

    def test_request_budget_is_bounded(self) -> None:
        self.guard.requests = 200
        with self.assertRaisesRegex(ValueError, "request budget"):
            self.guard.authorize("https://example.com")

    def test_chromium_loopback_bypass_is_disabled(self) -> None:
        options = chromium_proxy_options("http://127.0.0.1:9000")
        self.assertEqual(options["proxy"]["bypass"], "<-loopback>")
        self.assertIn("--disable-quic", options["args"])

    def test_ambiguous_urls_are_rejected(self) -> None:
        for url in (
            "https://example.com/\x00path", "https://example.com/\x7fpath",
            "https://example.com\\@127.0.0.1", "https://example.com./",
            "https://%65xample.com", "https://example..com", "https://exämple.com",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    extract_hostname(url)

    @patch("adaptive_qa.dns_resolver.resolve_with_deadline", return_value=("8.8.8.8",))
    def test_default_target_validation_uses_bounded_resolver(self, resolve) -> None:
        validate_target("https://example.com", self.project, DestinationPolicy())
        resolve.assert_called_once_with("example.com", 443)

    def test_sample_mode_requires_explicit_boolean(self) -> None:
        with self.assertRaises(ValueError):
            DestinationGuard(self.project, local_sample="false")


class BoundedDNSTests(unittest.TestCase):
    @patch("adaptive_qa.dns_resolver.subprocess.run")
    def test_resolver_subprocess_has_a_deadline(self, run) -> None:
        run.return_value = Mock(returncode=0, stdout='["8.8.8.8"]')
        self.assertEqual(resolve_with_deadline("example.com", 443), ("8.8.8.8",))
        self.assertEqual(run.call_args.kwargs["timeout"], 5)

    @patch("adaptive_qa.dns_resolver.subprocess.run")
    def test_timeout_and_invalid_dns_output_are_rejected(self, run) -> None:
        run.side_effect = subprocess.TimeoutExpired("dns", 5)
        with self.assertRaises(ValueError):
            resolve_with_deadline("example.com", 443)
        run.side_effect = None
        for output in ('[]', '{}', 'null', '[1]', 'invalid'):
            run.return_value = Mock(returncode=0, stdout=output)
            with self.subTest(output=output):
                with self.assertRaises(ValueError):
                    resolve_with_deadline("example.com", 443)


if __name__ == "__main__":
    unittest.main()
