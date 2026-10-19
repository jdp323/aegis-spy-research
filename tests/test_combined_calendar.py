import unittest,tempfile,json
from pathlib import Path
from datetime import datetime,timezone,timedelta
from core.sessions import ET
from news.calendar_updater import parse_fed,SOURCES,update,maintenance
from news.engine import NewsProvider
class CalendarUpgradeTests(unittest.TestCase):
 def test_date_only_during_dst_day(self):
  now=datetime(2026,10,8,tzinfo=timezone.utc)
  rows,_=parse_fed((Path(__file__).parent/'fixtures/official_calendar/fed.html').read_bytes(),SOURCES['fed'],now,date_only=True)
  self.assertTrue(rows);e=rows[0];start=datetime.fromisoformat(e['blackout_start_utc']);end=datetime.fromisoformat(e['blackout_end_utc'])
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'calendar.json';path.write_text(json.dumps({'source_url':SOURCES['fed'],'verified_at':start.isoformat(),'coverage_from':start.isoformat(),'coverage_through':end.isoformat(),'coverage_complete':True,'events':[e]}))
   self.assertEqual(NewsProvider(path).snapshot(start)['risk'],'HIGH');self.assertEqual(NewsProvider(path).snapshot(end)['risk'],'NORMAL')
  self.assertEqual(start.astimezone(ET).hour,0);self.assertEqual(end.astimezone(ET).hour,0)
 def test_failed_fetch_keeps_good(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'config').mkdir();p=root/'config/news_calendar.json';p.write_text('preserved')
   result=update(root,transport=lambda u:(_ for _ in ()).throw(OSError()))
   self.assertFalse(result['published']);self.assertEqual(p.read_text(),'preserved')
