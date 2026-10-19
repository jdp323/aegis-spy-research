import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
from datetime import datetime,timezone,timedelta
from core.storage import Store
from core.fill_flow import begin,execute
from data.models import quote
from options.ledger import Ledger
from options.trade_plan import exit_conditions,mismatch
from monitoring.simple_notifications import enabled,alerts,calendar_warning
NOW=datetime(2026,10,8,15,tzinfo=timezone.utc)
def q(symbol='SPY',bid=500,ask=500.02):return quote('alpaca-sip' if symbol=='SPY' else 'alpaca-opra',symbol,dict(bp=bid,ap=ask,t=NOW.isoformat()),received=NOW.isoformat()).view(NOW)
class FillAndSecurityTests(unittest.TestCase):
 def signal(self):
  symbol='SPY261014C00500000'
  return dict(signal_id='a'*24,timestamp=NOW.isoformat(),signal_expiry=(NOW+timedelta(minutes=10)).isoformat(),direction='CALL',spy_price=500,invalidation=499,t1=501,t2=502,option_contract={'symbol':symbol,'quote':q(symbol,2.3,2.4)},option_plan=dict(stop_bid=1.9,t1_bid=2.9,t2_bid=3.4,max_hold_until=(NOW+timedelta(hours=1)).isoformat()),horizon='SCALP')
 def test_actual_fill_auto_plan_and_idempotency(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'runtime').mkdir();s=Store(root/'runtime/aegis.sqlite')
   try:
    begin(s,self.signal(),now=NOW)
    for i,t in enumerate(('quantity 1','premium 3.10','fees .65','time 2026-10-08T15:00:05+00:00')):execute(s,t,'owner','fixture'+str(i),NOW+timedelta(seconds=10))
    with patch('options.command.ROOT',root):r=execute(s,'confirm yes','owner','fixture-confirm',NOW+timedelta(seconds=10))
    self.assertIn('RECORDED_USER_REPORT',r);self.assertEqual(s.get('plan:owner:SPY261014C00500000')['actual_entry'],3.1)
    ledger=Ledger(root/'options/reported.sqlite')
    try:self.assertEqual(ledger.positions()[0]['cost_usd'],'310.65')
    finally:ledger.close()
    self.assertIn('complete',execute(s,'confirm yes','owner','again',NOW+timedelta(seconds=10)))
    self.assertIn('expired',execute(s,'quantity 1','owner','later',NOW+timedelta(minutes=11)))
   finally:s.close()
 def test_dual_triggers_and_stale_fallback(self):
  s=self.signal();op=q(s['option_contract']['symbol'],3,3.1);p=s['option_plan']
  self.assertIn('T1_REVIEW',exit_conditions(p,s,q(),op,NOW)['conditions'])
  bad={**op,'entitlement':'INDICATIVE'};self.assertIsNone(exit_conditions(p,s,q(bid=501,ask=501.02),bad,NOW)['option_bid'])
  self.assertIn('T1_REVIEW',exit_conditions(p,s,q(bid=501,ask=501.02),bad,NOW)['conditions'])
  s.update(direction='PUT',invalidation=502,t1=499,t2=498);self.assertIn('T1_REVIEW',exit_conditions(p,s,q(bid=498.9,ask=499),bad,NOW)['conditions'])
 def test_mismatch_and_simple_toggles_private(self):
  self.assertTrue(mismatch([q(),q(bid=502,ask=502.02)],{},NOW))
  c={'notifications':{'profile':'simple'}};self.assertFalse(enabled(c,'periodic'));self.assertTrue(enabled(c,'ideas'))
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'config').mkdir();p=root/'config/upgrade.json';p.write_text(json.dumps(c))
   before=p.read_bytes();self.assertIn('Only the owner',alerts('ideas off','b'*24,root));self.assertEqual(before,p.read_bytes())
   self.assertIn('ideas: OFF',alerts('ideas off','owner',root))
