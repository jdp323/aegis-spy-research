import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
from data.credentials import child_environment,configured,validate,configure,NAMES

class ProtectedDataConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'market_data.dpapi';p=patch('data.credentials.PATH',self.path);p.start();self.addCleanup(p.stop)
    def test_missing_config_preserves_environment(self):
        self.assertEqual(child_environment({'TASK':'fixture'}),{'TASK':'fixture'})
    def test_existing_environment_keys_do_not_decrypt_file(self):
        with patch('data.credentials.transform') as decrypt:
            env={NAMES[0]:'synthetic-key',NAMES[1]:'synthetic-secret'}
            self.assertEqual(child_environment(env),env);decrypt.assert_not_called()
    def test_encrypted_payload_consumed_only_into_child_environment(self):
        self.path.write_bytes(b'ciphertext-fixture');fixture={NAMES[0]:'synthetic-key',NAMES[1]:'synthetic-secret'}
        with patch('data.credentials.transform',return_value=json.dumps(fixture).encode()):
            base={'TASK':'fixture'};self.assertEqual(child_environment(base)[NAMES[0]],fixture[NAMES[0]]);self.assertEqual(base,{'TASK':'fixture'})
    def test_bad_encrypted_payload_fails_closed_without_secret_in_error(self):
        self.path.write_bytes(b'ciphertext')
        with patch('data.credentials.transform',return_value=b'{"secret":"synthetic-private"}'):
            with self.assertRaisesRegex(RuntimeError,'MARKET_DATA_ENCRYPTED_CONFIG_UNREADABLE'):child_environment({})
    def test_noninteractive_configuration_rejected_before_input(self):
        with patch('data.credentials.sys.stdin.isatty',return_value=False),patch('data.credentials.getpass.getpass') as prompt:
            with self.assertRaises(RuntimeError):configure()
            prompt.assert_not_called();self.assertFalse(self.path.exists())
    def test_no_silent_overwrite_or_extra_fields(self):
        self.path.write_bytes(b'existing')
        with patch('data.credentials.sys.stdin.isatty',return_value=True),patch('data.credentials.getpass.getpass') as prompt:
            with self.assertRaises(RuntimeError):configure()
            prompt.assert_not_called();self.assertEqual(self.path.read_bytes(),b'existing')
        with self.assertRaises(ValueError):validate({'token':'unrelated'})

if __name__=='__main__':unittest.main()
