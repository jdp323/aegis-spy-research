import unittest,copy,tempfile
from pathlib import Path
from datetime import datetime,timezone,timedelta
from core.signals import build,Signal,finalize
from core.upgrade_service import read_config,validate_config
from core.readiness import evaluate
from data.models import quote
from backtesting.paper_engine import PaperEngine
NOW=datetime(2026,10,8,15,tzinfo=timezone.utc)
class PaperEligibilityTests(unittest.TestCase):
 def inputs(self):
  f={'atr14':1,'close':601,'structure':'HH_HL','trend':'BULL','rvol_same_slot':2,'vwap_approx':600,'macd':{'histogram':1},'timestamp':NOW.timestamp()-60}
  fs={k:dict(f) for k in ('1m','5m','15m','30m','1h','daily')};fs['opening_range']={'high':600,'low':599}
  q=quote('alpaca-sip','SPY',{'bp':601,'ap':601.02,'t':NOW.isoformat()},received=NOW.isoformat()).view(NOW)
  oq=quote('alpaca-opra','SPY261009C00600000',{'bp':2,'ap':2.1,'t':NOW.isoformat()},received=NOW.isoformat()).view(NOW)
  return [fs,{'regime':'BULL'},{'best_contract':{'symbol':oq['symbol'],'type':'C','strike':600,'expiry':'2026-10-09','bid':2,'ask':2.1,'quote':oq,'greeks_timestamp':NOW.isoformat(),'delta':.5,'gamma':.01,'theta':-.1,'vega':.1,'iv':.2,'volume':500,'oi':1000}},q,{'quality':'DATA_OK','risk':'NORMAL'},{'active':True,'date':'2026-10-08'},{'ready':True}]
 def test_flag_and_live_separation(self):
  for flag in (False,True):
   s=build(*self.inputs(),NOW,{'allow_unvalidated_paper_trading':flag});self.assertEqual(s.paper_eligible,flag);self.assertFalse(s.actionable);self.assertFalse(s.live_signal_ready);self.assertTrue(s.hard_rejection);self.assertIn('STRATEGY_PROSPECTIVE_VALIDATION_MISSING',s.rejection_reasons)
  self.assertFalse(evaluate({},read_config())['live_ready'])
 def test_each_other_gate(self):
  mutations=[(0,lambda f:f['1m'].update(timestamp=0)),(1,lambda r:r.update(regime='UNSAFE')),(2,lambda s:s.update(best_contract=None)),(3,lambda q:q.update(entitlement='INDICATIVE')),(4,lambda n:n.update(risk='HIGH')),(5,lambda s:s.update(active=False)),(6,lambda r:r.update(ready=False))]
  for idx,mutate in mutations:
   args=self.inputs();mutate(args[idx]);s=build(*args,NOW,{'allow_unvalidated_paper_trading':True});self.assertFalse(s.paper_eligible);self.assertTrue(s.paper_blockers)
 def test_paper_route_real_quotes_only(self):
  with tempfile.TemporaryDirectory() as tmp:
   s=build(*self.inputs(),NOW,{'allow_unvalidated_paper_trading':True});p=PaperEngine(Path(tmp)/'p.sqlite');self.assertEqual(p.open(s,s.option_contract['quote'],now=NOW)['status'],'OPEN');p.store.close()
  args=self.inputs();args[2]['best_contract']['quote']['provider']='indicative';self.assertFalse(build(*args,NOW,{'allow_unvalidated_paper_trading':True}).paper_eligible)
 def test_validator_never_promotes(self):
  c=read_config();self.assertTrue(c['allow_unvalidated_paper_trading']);self.assertFalse(c['options_risk_live_confirmed'])
  for key in ('order_execution_enabled','live_signal_enabled'):
   bad=copy.deepcopy(c);bad[key]=True
   with self.assertRaises(ValueError):validate_config(bad)
  c['allow_unvalidated_paper_trading']='true'
  with self.assertRaises(ValueError):validate_config(c)
 def test_stale_missing_greeks_and_liquidity_block_paper(self):
  for field,value in [('greeks_timestamp',None),('greeks_timestamp',(NOW-timedelta(seconds=61)).isoformat()),('volume',None),('oi',0),('iv',float('nan'))]:
   args=self.inputs();args[2]['best_contract'][field]=value;signal=build(*args,NOW,{'allow_unvalidated_paper_trading':True});self.assertFalse(signal.paper_eligible)
