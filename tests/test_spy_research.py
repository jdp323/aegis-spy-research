import unittest,json
from datetime import datetime,timezone
from core.spy_research import session,analyze
from data.public_spy import parse_chart
class ResearchTests(unittest.TestCase):
 def test_us_calendar(self):
  self.assertEqual(session(datetime(2026,10,12,14,tzinfo=timezone.utc))[0],'REGULAR_SESSION')
  self.assertEqual(session(datetime(2026,11,26,16,tzinfo=timezone.utc))[0],'CLOSED')
  self.assertEqual(session(datetime(2026,11,27,18,tzinfo=timezone.utc))[0],'AFTER_HOURS')
  self.assertEqual(session(datetime(2027,1,4,16,tzinfo=timezone.utc))[0],'REGULAR_SESSION')
  self.assertEqual(session(datetime(2028,1,4,16,tzinfo=timezone.utc))[0],'CALENDAR_REFRESH_REQUIRED')
 def test_missing_data_no_signal(self):
  x=analyze({'status':'UNAVAILABLE','source':'test','fetched_at':'test','bars':[]})
  self.assertFalse(x['signal_ready']);self.assertIsNone(x['levels'])
 def test_complete_regular_bars_only(self):
  now=datetime(2026,10,5,14,tzinfo=timezone.utc)
  b={'timestamp':now.timestamp()-60,'open':10,'high':11,'low':9,'close':10,'volume':100}
  d={'status':'TEST','source':'test','fetched_at':'test','bars':[b]}
  self.assertIsNone(analyze(d,now)['levels'])
  b['timestamp']=now.timestamp()-300
  r=analyze(d,now);self.assertEqual(r['levels']['bar_count'],1);self.assertFalse(r['signal_ready'])
 def test_wrong_symbol_rejected(self):
  with self.assertRaises(ValueError):parse_chart(json.dumps({'chart':{'result':[{'meta':{'symbol':'QQQ'}}]}}))
