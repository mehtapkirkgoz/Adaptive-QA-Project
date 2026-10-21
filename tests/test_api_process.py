"""Private transport retains contracts and cleans up on deadline/cancellation."""

from dataclasses import replace
import os
import subprocess
import unittest
from unittest.mock import patch

from adaptive_qa.api_catalog import API_BY_ID
from adaptive_qa.api_models import ApiConfiguration, JsonCheck, JsonOperator, JsonType
from adaptive_qa.api_process import decode_api_input, encode_api_input, run_isolated_api_case
from adaptive_qa.config import ProjectConfig
from adaptive_qa.models import TestStatus
from adaptive_qa.secrets import SecretReference


class ApiProcessTests(unittest.TestCase):
    def setUp(self):
        self.configuration = ApiConfiguration(ProjectConfig('api', 'API', 'http://127.0.0.1:8000', ('127.0.0.1',)),
                                               SecretReference('QA_API_PROCESS_TOKEN'))
        self.case = API_BY_ID['API-001']

    def test_private_roundtrip_preserves_enum_and_tuple_contracts(self):
        case = replace(self.case, checks=(JsonCheck((), JsonOperator.TYPE, JsonType.OBJECT),))
        with patch.dict(os.environ, {'QA_API_PROCESS_TOKEN': 'private-token'}):
            text = encode_api_input(case, self.configuration)
            self.assertNotIn('private-token', text)
            restored_case, restored_configuration = decode_api_input(text)
        self.assertEqual(restored_case, case)
        self.assertEqual(restored_configuration, self.configuration)

    def test_missing_configuration_and_mutations_do_not_spawn(self):
        with patch('adaptive_qa.api_process.subprocess.Popen') as popen:
            self.assertEqual(run_isolated_api_case(self.case, None).status, TestStatus.BLOCKED)
            self.assertEqual(run_isolated_api_case(API_BY_ID['API-014'], self.configuration).status, TestStatus.BLOCKED)
            popen.assert_not_called()

    def test_invalid_total_deadlines_are_rejected(self):
        for timeout in (True, 0, float('nan'), 61):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                run_isolated_api_case(self.case, self.configuration, timeout)

    def test_prestart_cancellation_does_not_spawn(self):
        with patch('adaptive_qa.api_process.subprocess.Popen') as popen:
            result = run_isolated_api_case(self.case, self.configuration, should_cancel=lambda: True)
            self.assertEqual(result.status, TestStatus.CANCELLED)
            popen.assert_not_called()

    @patch('adaptive_qa.api_process._terminate_process_tree')
    @patch('adaptive_qa.api_process.subprocess.Popen')
    def test_deadline_terminates_the_child(self, popen, terminate):
        process = popen.return_value
        process.poll.return_value = -1
        process.wait.side_effect = subprocess.TimeoutExpired('api', 1)
        with patch('adaptive_qa.api_process.perf_counter', side_effect=[0, 2, 2]):
            result = run_isolated_api_case(self.case, self.configuration, timeout_seconds=1)
        self.assertEqual(result.status, TestStatus.ERROR)
        terminate.assert_called_once_with(process)

    def test_invalid_child_result_does_not_pass(self):
        with patch('adaptive_qa.api_process.subprocess.Popen') as popen:
            popen.return_value.returncode = 0
            popen.return_value.poll.return_value = 0
            result = run_isolated_api_case(self.case, self.configuration)
        self.assertEqual(result.status, TestStatus.ERROR)
