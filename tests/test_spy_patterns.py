import unittest
from datetime import datetime,timezone
from features.spy_patterns import describe
class PatternTests(unittest.TestCase):
 def setUp(self):
  self.start=datetime(2026,10,5,13,30,tzinfo=timezone.utc).timestamp()
  self.bars=[{'timestamp':self.start+i*300,'open':10+i,'high':11+i,'low':9+i,'close':10.5+i,'volume':100} for i in range(5)]
  self.now=datetime(2026,10,5,14,tzinfo=timezone.utc)
 def test_observations_not_signal(self):
  r=describe(self.bars,self.now);self.assertEqual(r['opening_range_15m'],{'high':13,'low':9});self.assertEqual(r['structure_3bars'],'HIGHER_HIGHS_HIGHER_LOWS');self.assertEqual(r['action'],'NO TRADE')
 def test_incomplete_bar_excluded(self):
  before=datetime.fromtimestamp(self.start+299,timezone.utc);self.assertEqual(describe(self.bars,before)['status'],'INSUFFICIENT_DATA')
 def test_gap_never_infers_structure(self):
  r=describe([self.bars[0],self.bars[2],self.bars[4]],self.now);self.assertIsNone(r['opening_range_15m']);self.assertEqual(r['structure_3bars'],'UNAVAILABLE_GAPS_OR_HISTORY')
 def test_future_changes_cannot_change_earlier_result(self):
  t=datetime.fromtimestamp(self.start+900,timezone.utc);before=describe(self.bars,t);self.bars[4]['close']=9999;self.assertEqual(describe(self.bars,t),before)
