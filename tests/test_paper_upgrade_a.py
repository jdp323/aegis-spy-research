import unittest,tempfile,json
from pathlib import Path
from datetime import datetime,timezone,timedelta
from risk.options_policy import check,parse_limits
from backtesting.paper_engine import PaperEngine
from core.storage import ROOT
from core.upgrade_service import validate_config
class PaperRiskTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,10,8,2,tzinfo=timezone.utc)
        self.c={'max_trade_premium_usd':500.0,'max_exposure_usd':1500.0,'max_daily_loss_usd':300.0,'max_consecutive_losses':3,'daily_loss_usd':0,'consecutive_losses':0,'daily_reconciled_date':'2026-10-07'}
    def test_limits_and_live_confirmation(self):
        self.assertEqual(len(parse_limits(self.c)),4)
        self.assertFalse(check(self.c,[],now=self.now)['live_ready'])
        self.assertIn('LIVE_RISK_NOT_OWNER_CONFIRMED',check(self.c,[],now=self.now)['reasons'])
        self.assertTrue(check(self.c,[],now=self.now,mode='paper')['paper_ready'])
    def test_every_limit(self):
        for updates,positions,premium,reason in [({},[],501,'TRADE_PREMIUM_LIMIT'),({},[{'quantity':1,'cost_usd':'1500'}],None,'EXPOSURE_LIMIT'),({},[{'quantity':1,'cost_usd':'1200'}],400,'PROJECTED_EXPOSURE_LIMIT'),({'daily_loss_usd':300},[],None,'DAILY_CIRCUIT_BREAKER'),({'consecutive_losses':3},[],None,'LOSS_STREAK_COOLDOWN')]:
            with self.subTest(reason=reason):self.assertIn(reason,check({**self.c,**updates},positions,premium=premium,now=self.now,mode='paper')['reasons'])
    def test_auto_reconcile_utc_midnight_dst_and_separation(self):
        with tempfile.TemporaryDirectory() as d:
            p=PaperEngine(Path(d)/'db')
            p.store.event('loss','paper',{'signal_id':'a','status':'CLOSED','pnl_usd':'-12','closed_at':'2026-10-08T01:00:00+00:00'})
            a=p.risk_state(self.now);self.assertEqual(a['daily_reconciled_date'],'2026-10-07');self.assertEqual(a['daily_loss_usd'],12);self.assertEqual(a['consecutive_losses'],1)
            self.assertEqual(p.risk_state(self.now.replace(hour=4))['daily_loss_usd'],0)
            self.assertEqual(p.risk_state(datetime(2026,11,1,5,30,tzinfo=timezone.utc))['daily_reconciled_date'],'2026-11-01')
            self.assertEqual(p.risk_state(datetime(2026,11,1,6,30,tzinfo=timezone.utc))['daily_reconciled_date'],'2026-11-01')
            self.assertEqual(p.risk_state(datetime(2026,12,2,4,59,tzinfo=timezone.utc))['daily_reconciled_date'],'2026-12-01')
            self.assertEqual(p.risk_state(datetime(2026,12,2,5,tzinfo=timezone.utc))['daily_reconciled_date'],'2026-12-02')
            self.assertEqual(a['positions'],[])
            with self.assertRaises(ValueError):p.risk_state(datetime(2026,10,8))
            p.store.close()
    def test_configuration_cannot_enable_live(self):
        c=json.loads((ROOT/'config/upgrade.json').read_text());validate_config(c)
        for key in ('live_signal_enabled','order_execution_enabled'):
            with self.assertRaises(ValueError):validate_config({**c,key:True})
        with self.assertRaises(ValueError):validate_config({**c,'options_risk_live_confirmed':'true'})
