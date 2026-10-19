import unittest
from datetime import datetime,timezone,timedelta
from core.verdict import short,why
NOW=datetime(2026,10,8,15,tzinfo=timezone.utc)
class VerdictTests(unittest.TestCase):
 def sample(self,direction='CALL'):
  return dict(signal_expiry=(NOW+timedelta(minutes=10)).isoformat(),direction=direction,paper_eligible=True,paper_blockers=[],feed_quality='IEX',entry_condition='completed close confirmation',invalidation=500,t1=502,t2=503)
 def test_three_states_and_line_cap(self):
  for d in ('CALL','PUT'):
   t=short(self.sample(d),NOW);self.assertIn('BUY '+d+' idea',t);self.assertNotIn('bid 2.',t);self.assertLessEqual(len(t.splitlines()),15)
  s=self.sample();s['paper_blockers']=['NEWS_UNAVAILABLE_OR_BLACKOUT'];self.assertIn('NO TRADE',short(s,NOW));self.assertIn('calendar',short(s,NOW));self.assertIn('NEWS_UNAVAILABLE',why(s))
 def test_closed_and_simulated_rejection(self):
  self.assertIn('Market closed',short(self.sample(),NOW.replace(hour=23)))
  s=self.sample();s['feed_quality']='SIMULATED';self.assertIn('NO TRADE',short(s,NOW))
