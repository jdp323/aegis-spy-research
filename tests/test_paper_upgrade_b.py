import unittest,tempfile,json
from pathlib import Path
from datetime import datetime,timezone,timedelta
from core.sessions import ET
from news.engine import NewsProvider,validate
from news.calendar_updater import event,parse_bea,parse_fed,update,SOURCES
NOW=datetime(2026,10,8,15,tzinfo=timezone.utc)
class CalendarTests(unittest.TestCase):
 def calendar(self,e):return {'source_url':SOURCES['fed'],'verified_at':(NOW-timedelta(days=1)).isoformat(),'coverage_from':(NOW-timedelta(days=1)).isoformat(),'coverage_through':(NOW+timedelta(days=30)).isoformat(),'coverage_complete':True,'events':[e]}
 def snapshot(self,d,now):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'news.json';p.write_text(json.dumps(d));return NewsProvider(p).snapshot(now)
 def test_boundaries(self):
  e=event('CPI','CPI',NOW,SOURCES['fed'],NOW.isoformat());d=self.calendar(e)
  for seconds,risk in [(-1801,'NORMAL'),(-1800,'HIGH'),(900,'HIGH'),(901,'NORMAL')]:self.assertEqual(self.snapshot(d,NOW+timedelta(seconds=seconds))['risk'],risk)
 def test_fomc_override_moderate(self):
  e=event('FOMC','FOMC',NOW,SOURCES['fed'],NOW.isoformat());self.assertEqual(self.snapshot(self.calendar(e),NOW+timedelta(minutes=60))['risk'],'HIGH');self.assertEqual(self.snapshot(self.calendar(e),NOW+timedelta(minutes=60,seconds=1))['risk'],'NORMAL')
  e=event('PPI','PPI',NOW,SOURCES['fed'],NOW.isoformat());self.assertEqual(self.snapshot(self.calendar(e),NOW)['risk'],'MODERATE')
 def test_dst_source_validation(self):
  for month in (3,11):
   t=datetime(2026,month,9,8,30,tzinfo=ET);e=event('CPI','CPI',t,SOURCES['fed'],NOW.isoformat());validate(self.calendar(e));self.assertEqual(datetime.fromisoformat(e['time_utc']),t)
  d=self.calendar(e);d['events'][0]['source_url']='https://www.federalreserve.gov.evil.test/x'
  with self.assertRaises(ValueError):validate(d)
 def test_stale_coverage_and_preservation(self):
  e=event('CPI','CPI',NOW,SOURCES['fed'],NOW.isoformat());d=self.calendar(e)
  self.assertEqual(self.snapshot(d,NOW+timedelta(days=8))['risk'],'UNAVAILABLE');self.assertEqual(self.snapshot(d,NOW-timedelta(days=2))['risk'],'UNAVAILABLE')
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'config').mkdir();p=root/'config/news_calendar.json';p.write_text(json.dumps(d));before=p.read_bytes()
   def fail(url):raise OSError('fixture failure')
   r=update(root,NOW,fail);self.assertFalse(r['published']);self.assertEqual(p.read_bytes(),before);self.assertTrue(list((root/'research/calendar_attempts').glob('*.json')))
 def test_recorded_official_pages(self):
  fixture=Path(__file__).parent/'fixtures/official_calendar';rows,_=parse_bea((fixture/'bea.html').read_bytes(),SOURCES['bea'],NOW);self.assertTrue(rows);self.assertTrue(all(e['type'] in ('GDP','PCE') for e in rows))
  rows,unresolved=parse_fed((fixture/'fed.html').read_bytes(),SOURCES['fed'],NOW);self.assertFalse(rows);self.assertTrue(unresolved)
  with self.assertRaises(ValueError):parse_bea(b'not a schedule',SOURCES['bea'],NOW)
