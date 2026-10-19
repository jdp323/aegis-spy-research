import unittest
from core.preflight import protected_probe_status
class ProtectedProbeTests(unittest.TestCase):
    def test_encrypted_config_is_not_misreported_as_absent_or_live(self):
        original={'status':'FEED_NOT_CONFIGURED','action':'NO TRADE','quotes':{}}
        result=protected_probe_status(original,{'encrypted_config_present':True})
        self.assertEqual(result['status'],'DATA_INCOMPLETE')
        self.assertEqual(result['quotes'],{});self.assertEqual(result['action'],'NO TRADE')
        self.assertEqual(original['status'],'FEED_NOT_CONFIGURED')
    def test_missing_configuration_remains_unconfigured(self):
        original={'status':'FEED_NOT_CONFIGURED','quotes':{}}
        self.assertIs(protected_probe_status(original,{'encrypted_config_present':False}),original)
    def test_real_probe_failure_or_success_is_not_overridden_by_presence(self):
        for status in ('FEED_UNAVAILABLE_OR_INVALID','FRESH_QUOTES_RESEARCH_ONLY'):
            original={'status':status,'quotes':{},'action':'NO TRADE'}
            self.assertIs(protected_probe_status(original,{'encrypted_config_present':True}),original)
if __name__=='__main__':unittest.main()
