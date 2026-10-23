"""Plans cannot resolve credentials, downgrade submission policy or drift assertions."""
from dataclasses import replace
import unittest
from unittest.mock import patch

from adaptive_qa.config import ProjectConfig
from adaptive_qa.element_models import ElementMapping,LocatorSpec,LocatorStrategy
from adaptive_qa.interactive_contracts import FormOperation,InteractiveFormContract
from adaptive_qa.secrets import SecretReference,SecretValue


class InteractiveContractTests(unittest.TestCase):
    def contract(self):
        return InteractiveFormContract('a'*32,'b'*64,FormOperation.LOGIN,
            (SecretReference('LOCAL_TEST_USER'),SecretReference('LOCAL_TEST_PASSWORD')),
            ElementMapping('login.accepted',(LocatorSpec(LocatorStrategy.TEST_ID,'signed-in-panel'),)))

    def test_plan_never_resolves_inputs_or_contacts_targets(self):
        with patch.object(SecretReference,'resolve',side_effect=AssertionError('No credential access')),                 patch('socket.getaddrinfo',side_effect=AssertionError('No DNS')):
            contract = self.contract()
            config = ProjectConfig('a'*32,'Local','http://127.0.0.1:8000/',('127.0.0.1',),True)
            contract.validate_project(config,current_fingerprint='b'*64)
            self.assertEqual(len(contract.fingerprint()),64)
        self.assertTrue(contract.changes_data)
        self.assertEqual(contract.max_submissions,1)

    def test_plaintext_mismatched_and_untyped_contracts_are_rejected(self):
        contract = self.contract()
        for change in ({'inputs':('username','password')},{'inputs':(SecretValue('secret'),SecretValue('secret'))},
                       {'inputs':(SecretReference('SAME'),SecretReference('SAME'))}, {'operation':'login'},
                       {'inputs':(SecretReference('A'*161),SecretReference('PASSWORD'))},
                       {'timeout_seconds':True},{'timeout_seconds':999},{'configuration_fingerprint':'unknown'}):
            with self.subTest(change=tuple(change)),self.assertRaises(ValueError): replace(contract,**change)

    def test_permission_project_and_configuration_drift_block_submission_contract(self):
        contract = self.contract()
        config = ProjectConfig('a'*32,'Local','http://127.0.0.1:8000/',('127.0.0.1',),True)
        for candidate,fingerprint in ((replace(config,allow_data_changes=False),'b'*64),
                                      (replace(config,project_id='c'*32),'b'*64),(config,'d'*64)):
            with self.assertRaises(ValueError): contract.validate_project(candidate,current_fingerprint=fingerprint)

    def test_postcondition_and_input_reference_changes_invalidate_contract_digest(self):
        contract = self.contract()
        rejected = replace(contract,completion=ElementMapping('login.rejected',contract.completion.locators))
        changed_input = replace(contract,inputs=(SecretReference('OTHER_USER'),contract.inputs[1]))
        self.assertEqual(len({c.fingerprint() for c in (contract,rejected,changed_input)}),3)
        with self.assertRaises(ValueError):
            replace(contract,operation=FormOperation.SEARCH,inputs=(contract.inputs[0],))
        search = InteractiveFormContract('a'*32,'b'*64,FormOperation.SEARCH,(SecretReference('TEST_QUERY'),),
            ElementMapping('search.empty',(LocatorSpec(LocatorStrategy.TEST_ID,'no-results'),)))
        self.assertTrue(search.changes_data)
