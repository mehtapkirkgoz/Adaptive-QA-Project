import unittest
from adaptive_qa.demo_login_outcome import DemoProcessResult, diagnostic_from_message, PREFIX


class DemoOutcomeTests(unittest.TestCase):
    def test_only_bounded_codes_cross_the_result_boundary(self):
        for code in ('http_status_302','http_status_403','demo_tls_failed','demo_redirect_blocked'):
            result=DemoProcessResult('error',code,None)
            self.assertEqual(diagnostic_from_message(PREFIX+result.reason_code),code)
        for code in ('http_status_999','http_status_302 Cookie=private','https://private.test','raw response',None):
            self.assertIsNone(diagnostic_from_message(PREFIX+str(code)))
            with self.assertRaises(ValueError):DemoProcessResult('error',code,None)
        with self.assertRaises(ValueError):DemoProcessResult('accepted','response_accepted',0)


if __name__=='__main__':unittest.main()
