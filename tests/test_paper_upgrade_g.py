import unittest,tempfile
from pathlib import Path
from strategies.spy_setups import detect
from backtesting.forward_validation import ForwardValidation
from core.signals import Signal
from datetime import datetime,timezone
class SetupTests(unittest.TestCase):
 def features(self,sign):
  return {'5m':{'close':101 if sign==1 else 99,'vwap_approx':100,'previous_close':99 if sign==1 else 101,'previous_vwap_approx':100,'previous_low':98,'previous_high':102,'rvol_same_slot':2,'structure':'HH_HL' if sign==1 else 'LH_LL'},'15m':{'trend':'BULL' if sign==1 else 'BEAR'}}
 def test_reclaim_rejection_and_confirmations(self):
  for sign,setup in [(1,'VWAP_RECLAIM'),(-1,'VWAP_REJECTION')]:
   f=self.features(sign);r=detect(f,101 if sign==1 else 99);self.assertEqual(r['setup_type'],setup);self.assertFalse(r['reasons']);f['5m']['rvol_same_slot']=None;self.assertIn('VOLUME_CONFIRMATION_MISSING',detect(f,101 if sign==1 else 99)['reasons']);f['15m']['trend']='BEAR' if sign==1 else 'BULL';self.assertIn('HIGHER_TIMEFRAME_CONTRADICTS',detect(f,101 if sign==1 else 99)['reasons'])
 def test_rejected_evaluations_retained(self):
  with tempfile.TemporaryDirectory() as tmp:
   f=ForwardValidation(Path(tmp)/'f.sqlite');s=Signal('rejected',datetime(2026,10,8,15,tzinfo=timezone.utc).isoformat(),None,'fixture',score=None);f.record(s);f.record(s);self.assertEqual(f.db.execute('SELECT count(*) FROM forward_evaluations').fetchone()[0],0);self.assertEqual(f.db.execute('SELECT sum(evaluations) FROM forward_reason_counts').fetchone()[0],2);self.assertEqual(f.db.execute('SELECT count(*) FROM forward_outcomes').fetchone()[0],0);f.close()
