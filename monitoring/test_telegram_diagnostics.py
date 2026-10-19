import unittest
from urllib.error import HTTPError, URLError
from telegram_test import safe_error

class DiagnosticsTests(unittest.TestCase):
    def test_auth_error_excludes_secret_url_and_message(self):
        secret='SENSITIVE_TEST_VALUE'
        error=HTTPError('https://example.invalid/'+secret,401,secret,{},None)
        result=safe_error(error,'getMe')
        self.assertNotIn(secret,result)
        self.assertIn('HTTP 401',result)
        self.assertIn('No sample message was sent',result)

    def test_network_error_never_echoes_reason(self):
        result=safe_error(URLError('SENSITIVE_TEST_VALUE'),'getMe')
        self.assertNotIn('SENSITIVE_TEST_VALUE',result)
        self.assertIn('Network',result)

    def test_send_timeout_marks_delivery_uncertain(self):
        self.assertIn('Delivery is uncertain',safe_error(TimeoutError(),'sendMessage'))

    def test_local_error_redacts_details(self):
        result=safe_error(ValueError('SENSITIVE_TEST_VALUE'),'getMe')
        self.assertNotIn('SENSITIVE_TEST_VALUE',result)
        self.assertIn('ValueError',result)

if __name__=='__main__':
    unittest.main()
