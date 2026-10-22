import unittest
from datetime import timedelta
from test_complete_telegram_messages import idea,NOW
from data.models import quote
from options.research_contract import verified_plan
class VerifiedReference(unittest.TestCase):
 def selection(self):
  symbol='SPY261016C00500000';q=quote('alpaca-opra',symbol,{'bp':1.95,'ap':2.05,'t':NOW.isoformat()},received=NOW.isoformat()).view(NOW)
  return {'best_contract':dict(symbol=symbol,type='C',expiry='2026-10-16',strike=500,bid=1.95,ask=2.05,mid=2.,delta=.5,gamma=.01,theta=-.1,vega=.1,iv=.2,greeks_timestamp=NOW.isoformat(),volume=1000,oi=1000,quote=q),'chain_sanity_reasons':[]}
 def test_ask_reference_has_no_delta_stop_or_assumed_limit_fill(self):
  r=verified_plan(idea(),self.selection(),NOW,{})
  self.assertEqual(r['limit'],2.05);self.assertEqual(r['premium_at_risk'],205);self.assertFalse(r['fill_assumed']);self.assertIsNone(r['loss_at_stop']);self.assertNotIn('t2_bid',r)
 def test_missing_liquidity_or_old_greeks_or_unverified_chain_refuse(self):
  for mutation in ('liquidity','greeks','chain','source','terms'):
   s=self.selection()
   if mutation=='liquidity':s['best_contract']['volume']=None
   if mutation=='greeks':s['best_contract']['greeks_timestamp']=(NOW-timedelta(days=1)).isoformat()
   if mutation=='chain':s['chain_sanity_reasons']=['MISSING']
   if mutation=='source':s['best_contract']['quote']['source_timestamp']=(NOW-timedelta(seconds=6)).isoformat()
   if mutation=='terms':s['best_contract']['bid']=1.96
   with self.assertRaises(ValueError,msg=mutation):verified_plan(idea(),s,NOW,{})
