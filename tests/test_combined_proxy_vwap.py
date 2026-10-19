import unittest
from unittest.mock import patch
from datetime import datetime,timezone,timedelta
from data.models import quote
from backtesting.proxy_engine import candidate
from core.upgrade_service import read_config

class ProxyVWAPTests(unittest.TestCase):
 def test_call_put_vwap_confirmation_and_news_gate(self):
  now=datetime(2026,10,8,14,1,tzinfo=timezone.utc)
  for sign,expected in ((1,'VWAP_RECLAIM'),(-1,'VWAP_REJECTION')):
   rows=[]
   for i in range(31):
    rows.append(dict(t=(now-timedelta(minutes=31-i)).isoformat(),o=500,h=502,l=498,c=500,v=1000))
   rows[-2].update(c=500-sign*.2,l=499.5,h=500.5)
   rows[-1].update(c=500+sign*.3,l=499.7,h=500.3,v=2000)
   px=500+sign*.4;q=quote('alpaca-iex','SPY',{'bp':px-.01,'ap':px+.01,'t':now.isoformat()},received=now.isoformat()).view(now)
   data={'research_quote:SPY:iex':q,'research_stream_bars:SPY:iex':rows}
   class FakeStore:
    def get(self,key,default=None):return data.get(key,default)
   live=dict(status='LIVE_TREND',feed='iex',provider='alpaca-iex',direction='UP' if sign==1 else 'DOWN',bar_end=now.isoformat(),votes={})
   with patch('research.live_trend.evaluate',return_value=live),patch('backtesting.proxy_engine.calculate',return_value={'vwap_approx':500,'previous_vwap_approx':500,'trend':'BULL' if sign==1 else 'BEAR'}):
    s,_,_=candidate(FakeStore(),{'quality':'DATA_OK','risk':'NORMAL'},read_config(),now)
    self.assertEqual(s.setup_type,expected);self.assertEqual(s.strategy_version,'proxy-vwap-v1');self.assertTrue(s.paper_eligible,s.paper_blockers)
    s,_,_=candidate(FakeStore(),{'quality':'DATA_OK','risk':'HIGH'},read_config(),now)
    self.assertFalse(s.paper_eligible);self.assertIn('NEWS_UNAVAILABLE_OR_BLACKOUT',s.paper_blockers)
