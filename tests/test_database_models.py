"""Reject invalid database contracts before any connection is opened."""

from dataclasses import replace
import unittest
from unittest.mock import patch

from adaptive_qa.config import ProjectConfig
from adaptive_qa.database_models import (
    DatabaseCase, DatabaseCheck, DatabaseConfiguration, DatabaseOperator, QueryTemplate,
)
from adaptive_qa.models import TestCase, TestType
from adaptive_qa.secrets import SecretReference


class DatabaseModelTests(unittest.TestCase):
    def setUp(self):
        self.project = ProjectConfig('db', 'Database', 'http://127.0.0.1:8000', ('127.0.0.1',))
        self.definition = TestCase('DB-001', 'Record exists', TestType.DATABASE, (),
                                   ('Read the configured record',), 'One record exists.')
        self.template = QueryTemplate('db', 'record', 'SELECT id FROM records WHERE id = :id', ('id',))
        self.check = DatabaseCheck(DatabaseOperator.ROW_COUNT, 1)

    def test_contract_creation_never_opens_database_or_resolves_secret(self):
        with patch('sqlite3.connect', side_effect=AssertionError('Unexpected connection')), \
                patch.object(SecretReference, 'resolve', side_effect=AssertionError('Unexpected resolution')):
            config = DatabaseConfiguration(self.project, SecretReference('QA_DB_PATH'))
            case = DatabaseCase(self.definition, self.template, (('id', 1),), (self.check,))
        self.assertEqual(config.max_rows, 100)
        self.assertEqual(case.template.project_id, self.project.project_id)

    def test_configuration_rejects_raw_paths_and_unbounded_limits(self):
        with self.assertRaises(ValueError):
            DatabaseConfiguration(self.project, 'private.db')
        for values in ({'timeout_seconds': True}, {'timeout_seconds': float('nan')},
                       {'timeout_seconds': 11}, {'max_rows': 0}, {'max_rows': True},
                       {'max_result_bytes': 1048577}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                DatabaseConfiguration(self.project, SecretReference('QA_DB_PATH'), **values)

    def test_parameters_require_exact_unique_names(self):
        for values in ((), (('other', 1),), (('id', 1), ('id', 2)), [('id', 1)], (('id',),)):
            with self.subTest(values=values), self.assertRaises(ValueError):
                DatabaseCase(self.definition, self.template, values, (self.check,))

    def test_parameter_values_are_bounded_immutable_scalars(self):
        for value in ([], {}, b'bytes', float('inf'), 2**63, 'x' * 4097, '\ud800'):
            with self.subTest(value_type=type(value)), self.assertRaises(ValueError):
                DatabaseCase(self.definition, self.template, (('id', value),), (self.check,))

    def test_private_operands_are_absent_from_representations_and_errors(self):
        template = replace(self.template, sql='SELECT :id /* private-sql */')
        case = DatabaseCase(self.definition, template, (('id', 'private-value'),),
                            (DatabaseCheck(DatabaseOperator.CELL_EQUALS, 'private-expected'),))
        for private in ('private-sql', 'private-value', 'private-expected'):
            self.assertNotIn(private, repr(case))
        with self.assertRaises(ValueError) as failure:
            replace(case, parameters=(('id', 'private-value' * 1000),))
        self.assertNotIn('private-value', str(failure.exception))

    def test_wrong_layer_and_write_definitions_are_rejected(self):
        for definition in (replace(self.definition, test_type=TestType.UI),
                           replace(self.definition, changes_data=True)):
            with self.assertRaises(ValueError):
                DatabaseCase(definition, self.template, (('id', 1),), (self.check,))

    def test_query_metadata_and_encoding_are_validated(self):
        for values in ({'sql': ''}, {'sql': 'SELECT\x00'}, {'sql': '\ud800'},
                       {'parameter_names': ('id', 'id')}, {'parameter_names': ['id']},
                       {'template_id': 'unsafe-name'}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                replace(self.template, **values)

    def test_assertions_require_typed_operators_and_valid_cell_coordinates(self):
        for values in ({'operator': 'row_count'}, {'expected': True}, {'expected': -1},
                       {'row': True}, {'row': 1}, {'column': 100}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                replace(self.check, **values)
        for value in (None, False, 1, 1.5, 'value'):
            self.assertEqual(DatabaseCheck(DatabaseOperator.CELL_EQUALS, value).expected, value)

    def test_cases_require_nonempty_bounded_typed_assertions(self):
        for checks in ((), [self.check], ('check',), (self.check,) * 51):
            with self.subTest(count=len(checks)), self.assertRaises(ValueError):
                DatabaseCase(self.definition, self.template, (('id', 1),), checks)


if __name__ == '__main__':
    unittest.main()
