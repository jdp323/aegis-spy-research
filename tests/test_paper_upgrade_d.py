import unittest,tempfile
from pathlib import Path
from datetime import datetime,timezone,timedelta
from backtesting.proxy_engine import ProxyEngine,MODE
from core.signals import Signal
from data.models import quote
from core.upgrade_service import read_config
NOW=datetime(2026,10,8,15,tzinfo=timezone.utc)
class ProxyTests(unittest.TestCase):
 def signal(self,sign=1,now=NOW):return Signal('test',now.isoformat(),now.isoformat(),'alpaca-iex',paper_eligible=True,paper_mode=MODE,feed_quality='IEX',direction='CALL' if sign==1 else 'PUT',score=100,invalidation=99 if sign==1 else 101,t1=101.5 if sign==1 else 98.5,t2=102 if sign==1 else 98,signal_expiry=(now+timedelta(minutes=10)).isoformat())
 def bar(self,now=NOW,high=102.5,low=98.5):return {'t':now.isoformat(),'o':100,'c':100,'h':high,'l':low,'v':1000}
 def run_trade(self,sign=1,now=NOW,news=None,bar=None):
  tmp=tempfile.TemporaryDirectory();p=ProxyEngine(Path(tmp.name)/'p.sqlite');q=quote('alpaca-iex','SPY',{'bp':99.99,'ap':100.01,'t':now.isoformat()},received=now.isoformat()).view(now);opened=p.open(self.signal(sign,now),q,read_config(),now);updates=p.mark([bar or self.bar(now)],news or {'quality':'DATA_OK','risk':'NORMAL'},now+timedelta(minutes=1));return tmp,p,opened,updates
 def test_fills_stop_first_mfe_mae_separate_tables(self):
  for sign in (1,-1):
   tmp,p,e,changes=self.run_trade(sign)
   try:
    self.assertAlmostEqual(e['entry'],100.02 if sign==1 else 99.98);r=changes[-1];self.assertEqual(r['exit_reason'],'STOP_INVALIDATION');self.assertEqual(r['feed_quality'],'IEX');self.assertGreater(r['mfe_usd_per_share'],0);self.assertLess(r['mae_usd_per_share'],0);self.assertFalse(p.store.events('paper'));self.assertEqual(p.summary()['proxy']['closed'],1);self.assertEqual(p.summary()['matched_clock_random_direction_baseline']['closed'],1)
   finally:p.close();tmp.cleanup()
 def test_forced_flat_and_dst(self):
  for now in (datetime(2026,10,8,19,54,tzinfo=timezone.utc),datetime(2026,11,9,20,54,tzinfo=timezone.utc),datetime(2026,11,27,17,54,tzinfo=timezone.utc)):
   tmp,p,e,changes=self.run_trade(now=now,bar=self.bar(now,100.5,99.5))
   try:self.assertEqual(changes[-1]['exit_reason'],'FORCED_FLAT')
   finally:p.close();tmp.cleanup()
 def test_news_time_target_and_no_early_bar(self):
  tmp,p,e,changes=self.run_trade(news={'quality':'DATA_OK','risk':'HIGH'},bar=self.bar(high=100.5,low=99.5))
  try:self.assertEqual(changes[-1]['exit_reason'],'NEWS_BLACKOUT')
  finally:p.close();tmp.cleanup()
  tmp,p,e,changes=self.run_trade(bar=self.bar(high=102.5,low=99.5))
  try:self.assertEqual(changes[-1]['exit_reason'],'T2_REACHED')
  finally:p.close();tmp.cleanup()
 def test_no_indicative_or_proxy_option_route(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=ProxyEngine(Path(tmp)/'p.sqlite');q=quote('alpaca-iex','SPY',{'bp':99.99,'ap':100.01,'t':NOW.isoformat()},received=NOW.isoformat()).view(NOW);q['entitlement']='INDICATIVE'
   with self.assertRaises(ValueError):p.open(self.signal(),q,read_config(),NOW)
   p.close()
