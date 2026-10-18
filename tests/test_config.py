"""Tests for project configuration and target authorization."""

import unittest

from adaptive_qa.config import ProjectConfig


class ProjectConfigTests(unittest.TestCase):
    def make_project(self, **overrides: object) -> ProjectConfig:
        values = {
            "project_id": "demo",
            "name": "Demo Project",
            "base_url": "https://example.com",
            "allowed_hosts": ("example.com",),
            "allow_data_changes": False,
        }
        values.update(overrides)
        return ProjectConfig(**values)

    def test_base_url_requires_an_allowed_host(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "base_url must match an allowed host",
        ):
            self.make_project(base_url="https://other.example")

    def test_allowed_host_accepts_different_paths(self) -> None:
        project = self.make_project()

        self.assertTrue(
            project.is_url_allowed("https://example.com/login")
        )

    def test_unlisted_host_is_rejected(self) -> None:
        project = self.make_project()

        self.assertFalse(
            project.is_url_allowed("https://other.example")
        )

    def test_subdomain_requires_explicit_permission(self) -> None:
        project = self.make_project()

        self.assertFalse(
            project.is_url_allowed("https://admin.example.com")
        )

    def test_hostname_suffix_does_not_grant_permission(self) -> None:
        project = self.make_project()

        self.assertFalse(
            project.is_url_allowed("https://example.com.attacker.test")
        )

    def test_explicitly_allowed_subdomain_is_accepted(self) -> None:
        project = self.make_project(
            allowed_hosts=("example.com", "admin.example.com")
        )

        self.assertTrue(
            project.is_url_allowed("https://admin.example.com")
        )

    def test_url_hostname_is_case_insensitive(self) -> None:
        project = self.make_project()

        self.assertTrue(
            project.is_url_allowed("https://EXAMPLE.COM/login")
        )

    def test_unsupported_scheme_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "url must use HTTP or HTTPS",
        ):
            self.make_project(base_url="ftp://example.com")

    def test_embedded_credentials_are_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "url must not contain credentials",
        ):
            self.make_project(
                base_url="https://user:password@example.com"
            )

    def test_invalid_port_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "url is invalid"):
            self.make_project(base_url="https://example.com:invalid")

    def test_allowed_hosts_reject_invalid_entries(self) -> None:
        invalid_hosts = (
            "",
            "EXAMPLE.COM",
            "*.example.com",
            "example.com:443",
            "https://example.com",
            "example.com/path",
            "example .com",
        )

        for host in invalid_hosts:
            with self.subTest(host=host):
                with self.assertRaises(ValueError):
                    self.make_project(allowed_hosts=(host,))

    def test_allowed_hosts_require_a_non_empty_tuple(self) -> None:
        for hosts in ((), ["example.com"], None):
            with self.subTest(hosts=hosts):
                with self.assertRaisesRegex(
                    ValueError,
                    "allowed_hosts must be a non-empty tuple",
                ):
                    self.make_project(allowed_hosts=hosts)

    def test_project_fields_reject_blank_values(self) -> None:
        for field_name in ("project_id", "name"):
            with self.subTest(field=field_name):
                with self.assertRaisesRegex(
                    ValueError,
                    f"{field_name} must be a non-empty string",
                ):
                    self.make_project(**{field_name: "   "})

    def test_data_changes_are_disabled_by_default(self) -> None:
        project = self.make_project()

        self.assertFalse(project.allow_data_changes)

    def test_data_changes_reject_non_boolean_values(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "allow_data_changes must be a bool",
        ):
            self.make_project(allow_data_changes="false")


if __name__ == "__main__":
    unittest.main()