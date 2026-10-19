import unittest,tempfile,json,hashlib
from pathlib import Path
from datetime import datetime,timezone,timedelta
from news.calendar_import import load
from news.fred_calendar import collect
NOW=datetime(2026,10,9,tzinfo=timezone.utc)
class V5Import(unittest.TestCase):
 def test_hash_official_host_age_and_ics(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'bls.ics';body=b'BEGIN:VCALENDAR\nBEGIN:VEVENT\nSUMMARY:Consumer Price Index\nDTSTART:20261014T123000Z\nEND:VEVENT\nEND:VCALENDAR';p.write_bytes(body)
   side={'source_url':'https://www.bls.gov/schedule/news_release/bls.ics','downloaded_at':NOW.isoformat(),'sha256':hashlib.sha256(body).hexdigest()};sp=p.with_suffix('.ics.provenance.json');sp.write_text(json.dumps(side))
   groups,errors=load(d,NOW);self.assertFalse(errors);self.assertEqual(groups['bls']['events'][0]['time_et'],'2026-10-14T08:30:00-04:00')
   for bad in ({**side,'sha256':'0'*64},{**side,'source_url':'https://fake.example/calendar.ics'},{**side,'downloaded_at':(NOW-timedelta(days=8)).isoformat()}):
    sp.write_text(json.dumps(bad));self.assertFalse(load(d,NOW)[0])
 def test_fred_absent_date_only_no_key_in_status(self):
  rows,status=collect(NOW,path=Path('definitely-absent-v5.dpapi'));self.assertFalse(rows);self.assertEqual(status['status'],'FRED_NOT_CONFIGURED')
  rows,status=collect(NOW,key='a'*32,transport=lambda _: {'count':1,'release_dates':[{'release_name':'Consumer Price Index','date':'2026-11-04'}]})
  self.assertTrue(rows[0]['all_day']);self.assertEqual(rows[0]['time_et'],'2026-11-04T00:00:00-05:00');self.assertNotIn('a'*32,json.dumps(status));self.assertIn('not endorsed',status['notice'])
