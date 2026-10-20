"""Validate configuration boundaries before browser matching is implemented."""

from dataclasses import FrozenInstanceError
import unittest

from adaptive_qa.element_models import (
    ElementMapping, LocatorSpec, LocatorStrategy, MatchResult, MatchStatus, ProjectElementMappings,
)


class ElementModelTests(unittest.TestCase):
    def setUp(self):
        self.role = LocatorSpec(LocatorStrategy.ROLE, 'Sign in', role='button')
        self.default = ElementMapping('login.submit', (self.role,))

    def test_role_label_and_test_id_alternatives_are_supported(self):
        mapping = ElementMapping('login.username', (
            LocatorSpec(LocatorStrategy.ROLE, 'Email', role='textbox'),
            LocatorSpec(LocatorStrategy.LABEL, 'Email address'),
            LocatorSpec(LocatorStrategy.TEST_ID, 'username'),
        ), scope_test_id='login-form')
        self.assertEqual(len(mapping.locators), 3)

    def test_plain_strategy_strings_and_invalid_roles_are_rejected(self):
        for strategy, role in (('role', 'button'), (LocatorStrategy.ROLE, None),
                               (LocatorStrategy.ROLE, 'botton'), (LocatorStrategy.LABEL, 'textbox')):
            with self.subTest(strategy=strategy, role=role), self.assertRaises(ValueError):
                LocatorSpec(strategy, 'Sign in', role)

    def test_names_and_values_reject_blank_controls_and_excessive_length(self):
        for value in ('', ' ', 'Login\nSubmit', 'x' * 161):
            with self.subTest(value=value[:20]), self.assertRaises(ValueError):
                LocatorSpec(LocatorStrategy.LABEL, value)
        for name in ('Login.submit', 'login..submit', 'login submit', 'login.1button'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                ElementMapping(name, (self.role,))

    def test_empty_lists_untyped_and_duplicate_alternatives_are_rejected(self):
        for locators in ((), [self.role], ('button',), (self.role, self.role)):
            with self.subTest(locators=locators), self.assertRaises(ValueError):
                ElementMapping('login.submit', locators)
        with self.assertRaises(ValueError):
            ElementMapping('login.submit', tuple(LocatorSpec(LocatorStrategy.TEST_ID, str(i)) for i in range(21)))

    def test_scope_identifier_is_validated(self):
        for scope in ('', '\n', False):
            with self.subTest(scope=scope), self.assertRaises(ValueError):
                ElementMapping('login.submit', (self.role,), scope_test_id=scope)

    def test_project_override_replaces_default_alternatives(self):
        override = ElementMapping('login.submit', (LocatorSpec(LocatorStrategy.TEST_ID, 'enter'),))
        project = ProjectElementMappings('demo', (override,))
        self.assertIs(project.resolve(self.default, project_id='demo'), override)
        self.assertNotIn(self.role, project.resolve(self.default, project_id='demo').locators)

    def test_unmapped_control_keeps_default(self):
        self.assertIs(ProjectElementMappings('demo').resolve(self.default, project_id='demo'), self.default)

    def test_project_identity_cannot_be_mixed(self):
        with self.assertRaises(ValueError):
            ProjectElementMappings('demo').resolve(self.default, project_id='other')

    def test_duplicate_logical_names_and_invalid_project_collections_are_rejected(self):
        for mappings in ([self.default], (self.default, self.default), ('invalid',)):
            with self.subTest(mappings=mappings), self.assertRaises(ValueError):
                ProjectElementMappings('demo', mappings)

    def test_valid_match_statuses_preserve_invariants(self):
        for status, count, indexes in ((MatchStatus.MATCHED, 1, (0, 1)),
                                       (MatchStatus.AMBIGUOUS, 2, (0,)),
                                       (MatchStatus.MISSING, 0, ()), (MatchStatus.ERROR, 0, ())):
            with self.subTest(status=status):
                self.assertEqual(MatchResult('login.submit', status, count, 'Explicit result.', indexes).status, status)

    def test_inconsistent_status_counts_and_indexes_are_rejected(self):
        for status, count, indexes in ((MatchStatus.MATCHED, 2, (0,)), (MatchStatus.MATCHED, 1, ()),
                                       (MatchStatus.AMBIGUOUS, 1, (0,)), (MatchStatus.MISSING, 1, ()),
                                       (MatchStatus.ERROR, 0, (0,)), (MatchStatus.MATCHED, True, (0,))):
            with self.subTest(status=status, count=count), self.assertRaises(ValueError):
                MatchResult('login.submit', status, count, 'Invalid result.', indexes)

    def test_raw_status_and_invalid_rule_indexes_are_rejected(self):
        for status, indexes in (('matched', (0,)), (MatchStatus.MATCHED, [0]),
                                (MatchStatus.MATCHED, (True,)), (MatchStatus.MATCHED, (20,)),
                                (MatchStatus.MATCHED, (0, 0))):
            with self.subTest(status=status, indexes=indexes), self.assertRaises(ValueError):
                MatchResult('login.submit', status, 1, 'Invalid result.', indexes)

    def test_contracts_are_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            self.default.logical_name = 'other'


if __name__ == '__main__':
    unittest.main()
