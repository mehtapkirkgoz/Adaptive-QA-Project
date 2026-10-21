"""Tests for conservative page feature detection without network access."""

import unittest

from adaptive_qa.discovery import (
    FieldSnapshot, FormSnapshot, LinkSnapshot, PageSnapshot, detect_page_features,
)
from adaptive_qa.models import FeatureStatus


class PageDiscoveryTests(unittest.TestCase):
    def findings(self, **values):
        snapshot = PageSnapshot("https://example.com", **values)
        return {finding.feature: finding for finding in detect_page_features(snapshot)}

    def login_form(self, button="Sign in", visible=True):
        return FormSnapshot(fields=(FieldSnapshot("email"), FieldSnapshot("password")),
                            buttons=(button,), visible=visible)

    def test_login_requires_matching_fields_and_action_in_same_form(self):
        result = self.findings(forms=(self.login_form(),))
        self.assertEqual(result["login"].status, FeatureStatus.PRESENT)
        self.assertEqual(result["login"].evidence, ("form[0]",))
        self.assertEqual(result["login"].scope, "page")

    def test_turkish_and_english_button_variants_are_normalized(self):
        for button in ("GİRİŞ YAP", "Oturum aç", "  LOG IN  ", "Sign-in"):
            with self.subTest(button=button):
                result = self.findings(forms=(self.login_form(button),))
                self.assertEqual(result["login"].status, FeatureStatus.PRESENT)

    def test_registration_form_is_not_assumed_to_be_login(self):
        result = self.findings(forms=(self.login_form("Create account"),), collection_complete=True)
        self.assertEqual(result["login"].status, FeatureStatus.UNKNOWN)

    def test_fields_from_separate_forms_are_not_combined(self):
        forms = (FormSnapshot(fields=(FieldSnapshot("password"),)),
                 FormSnapshot(fields=(FieldSnapshot("email"),), buttons=("Sign in",)))
        self.assertEqual(self.findings(forms=forms)["login"].status, FeatureStatus.UNKNOWN)

    def test_hidden_form_does_not_prove_visible_login(self):
        result = self.findings(forms=(self.login_form(visible=False),))
        self.assertEqual(result["login"].status, FeatureStatus.UNKNOWN)

    def test_search_role_and_query_input_prove_search(self):
        form = FormSnapshot(role="search", fields=(FieldSnapshot("text"),), buttons=("Go",))
        self.assertEqual(self.findings(forms=(form,))["search"].status, FeatureStatus.PRESENT)

    def test_query_input_without_action_is_ambiguous(self):
        form = FormSnapshot(fields=(FieldSnapshot("search"),))
        self.assertEqual(self.findings(forms=(form,))["search"].status, FeatureStatus.UNKNOWN)

    def test_login_link_is_only_a_hint(self):
        result = self.findings(links=(LinkSnapshot("Account", "/login"),), collection_complete=True)
        self.assertEqual(result["login"].status, FeatureStatus.UNKNOWN)
        self.assertTrue(result["login"].evidence)

    def test_complete_page_can_report_page_scoped_absence(self):
        result = self.findings(collection_complete=True)
        for finding in result.values():
            self.assertEqual(finding.status, FeatureStatus.ABSENT)
            self.assertIn("not site-wide", finding.reason)

    def test_incomplete_page_does_not_prove_absence(self):
        for finding in self.findings().values():
            self.assertEqual(finding.status, FeatureStatus.UNKNOWN)

    def test_invalid_snapshot_collections_and_flags_are_rejected(self):
        for values in ({"forms": []}, {"links": ("/login",)}, {"collection_complete": "true"}):
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    PageSnapshot("https://example.com", **values)

    def test_hidden_fields_do_not_satisfy_login(self):
        form = FormSnapshot(fields=(FieldSnapshot("email"), FieldSnapshot("password", visible=False)),
                            buttons=("Sign in",))
        self.assertNotEqual(self.findings(forms=(form,))["login"].status, FeatureStatus.PRESENT)

    def test_passwordless_login_action_is_unknown_instead_of_absent(self):
        form = FormSnapshot(fields=(FieldSnapshot("email"),), buttons=("Sign in",))
        self.assertEqual(self.findings(forms=(form,), collection_complete=True)["login"].status,
                         FeatureStatus.UNKNOWN)

    def test_new_password_field_does_not_prove_login(self):
        form = FormSnapshot(fields=(FieldSnapshot("email"),
                                    FieldSnapshot("password", autocomplete="new-password")),
                            buttons=("Sign in",))
        self.assertEqual(self.findings(forms=(form,))["login"].status, FeatureStatus.UNKNOWN)

    def test_native_form_fields_supply_general_form_evidence(self):
        result = self.findings(forms=(FormSnapshot(fields=(FieldSnapshot('email'),)),))
        self.assertEqual(result['forms'].status, FeatureStatus.PRESENT)
        self.assertEqual(result['forms'].evidence, ('form[0]',))

    def test_navigation_requires_a_supported_link_target(self):
        for href, expected in (('/account', FeatureStatus.PRESENT),
                               ('#login', FeatureStatus.PRESENT),
                               ('javascript:alert(1)', FeatureStatus.ABSENT)):
            with self.subTest(href=href):
                result = self.findings(links=(LinkSnapshot('Account', href),), collection_complete=True)
                self.assertEqual(result['navigation'].status, expected)


if __name__ == "__main__":
    unittest.main()
