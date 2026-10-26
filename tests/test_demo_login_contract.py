import unittest

from adaptive_qa.demo_login_contract import (
    AUTHENTICATE, LOGIN, LOGOUT, SECURE, DemoLoginPlan, DemoLoginScenario,
)


class DemoLoginContractTests(unittest.TestCase):
    def test_scenarios_have_distinct_postconditions_without_execution_authority(self):
        for scenario in DemoLoginScenario:
            plan = DemoLoginPlan(scenario)
            self.assertFalse(plan.execution_authorized)
            self.assertEqual(plan.max_submissions, 1)
            expected = LOGIN if scenario == DemoLoginScenario.REJECTED else SECURE
            self.assertEqual(plan.redirect_destination(AUTHENTICATE, 303, expected), expected)
            self.assertEqual(plan.redirect_destination(AUTHENTICATE, 303, expected.split('.com')[1]), expected)
        self.assertIn('invalid', DemoLoginPlan(DemoLoginScenario.REJECTED).expected_message)

    def test_only_explicit_logout_scenario_has_logout_transition(self):
        self.assertEqual(DemoLoginPlan(DemoLoginScenario.LOGOUT).redirect_destination(LOGOUT, 302, '/login'), LOGIN)
        for scenario in (DemoLoginScenario.ACCEPTED, DemoLoginScenario.REJECTED):
            with self.assertRaises(ValueError):
                DemoLoginPlan(scenario).redirect_destination(LOGOUT, 302, '/login')

    def test_redirects_cannot_escape_exact_demo_routes(self):
        plan = DemoLoginPlan(DemoLoginScenario.ACCEPTED)
        for location in ('//other.example/secure', 'https://other.example/secure',
                         'http://the-internet.herokuapp.com/secure', '/secure?next=bad',
                         '/secure#fragment', '/secure/', '/login', '/%73ecure',
                         'https://the-internet.herokuapp.com:443/secure', None):
            with self.assertRaises(ValueError):
                plan.redirect_destination(AUTHENTICATE, 303, location)
        for status in (200, 301, 302, 307, 308, '302', True):
            with self.assertRaises(ValueError):
                plan.redirect_destination(AUTHENTICATE, status, '/secure')
        with self.assertRaises(ValueError):
            plan.redirect_destination(LOGIN, 302, '/secure')

    def test_raw_or_unknown_scenarios_are_rejected(self):
        for value in ('accepted_login', 'arbitrary_site', None, True):
            with self.assertRaises(ValueError):
                DemoLoginPlan(value)


if __name__ == '__main__':
    unittest.main()
