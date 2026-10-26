import unittest
from unittest.mock import patch

from adaptive_qa.demo_login_contract import LOGIN, AUTHENTICATE, DemoLoginPlan, DemoLoginScenario
from adaptive_qa.demo_login_transport import DemoLoginTransport, demo_body


class DemoLoginTransportTests(unittest.TestCase):
    def test_malformed_attempt_consumes_scope_before_dns(self):
        for method, url, body in [('POST', AUTHENTICATE, b'x'), ('GET', LOGIN+'?x=1', None),
                                  ('GET', 'https://other.example/login', None), ('GET', LOGIN, b'x')]:
            transport = DemoLoginTransport(DemoLoginPlan(DemoLoginScenario.ACCEPTED))
            with patch.object(transport.guard, 'authorize') as authorize:
                with self.assertRaises(ValueError):
                    transport.request(method, url, body)
                with self.assertRaises(ValueError):
                    transport.request('GET', LOGIN)
                authorize.assert_not_called()

    def test_failed_connection_is_not_retried(self):
        transport = DemoLoginTransport(DemoLoginPlan(DemoLoginScenario.ACCEPTED))
        with patch.object(transport.guard, 'authorize', side_effect=OSError()) as authorize:
            with self.assertRaises(OSError):
                transport.request('GET', LOGIN)
            with self.assertRaises(ValueError):
                transport.request('GET', LOGIN)
            self.assertEqual(authorize.call_count, 1)

    def test_only_rejected_scenario_uses_wrong_public_demo_password(self):
        accepted = demo_body(DemoLoginPlan(DemoLoginScenario.ACCEPTED))
        self.assertEqual(accepted, demo_body(DemoLoginPlan(DemoLoginScenario.LOGOUT)))
        self.assertNotEqual(accepted, demo_body(DemoLoginPlan(DemoLoginScenario.REJECTED)))
        with self.assertRaises(ValueError):
            DemoLoginTransport('accepted_login')


if __name__ == '__main__': unittest.main()
