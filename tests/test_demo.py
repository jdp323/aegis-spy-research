import unittest
import tempfile
from core.demo import run_demo

class DemoTests(unittest.TestCase):
    def test_synthetic_lifecycle(self):
        with tempfile.TemporaryDirectory() as folder:
            demo=run_demo(folder)['result']
        self.assertTrue(demo['demo'])
        self.assertEqual(demo['buy']['status'],'PENDING_RESEARCH_ONLY')
        self.assertFalse(demo['buy']['execution_authorized'])
        self.assertEqual(demo['duplicate']['status'],'REJECTED')
        self.assertEqual(demo['stale_quote']['status'],'REJECTED')
        self.assertEqual(demo['expiry'],'EXPIRED_REVIEW_REQUIRED')
        self.assertEqual(demo['sell']['status'],'PENDING_RESEARCH_ONLY')
        self.assertEqual(demo['profit_cycle']['protectedreserve'],'51.00')
        self.assertEqual(demo['profit_cycle']['tradingcash'],'1.60')

if __name__=='__main__':unittest.main()
