"""Event-date display fixtures; no provider calls, live events or sends."""
import copy, unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from monitoring.owner_messages import next_event, premarket_text
ET=ZoneInfo('America/New_York')
NOW=datetime(2026,11,2,9,15,tzinfo=ET)
def event(at, name='Employment Situation', date_only=False):
    return dict(name=name,time_utc=at.astimezone(timezone.utc).isoformat(),**({'time_source':'DATE_ONLY'} if date_only else {}))
def news(*rows):return dict(quality='DATA_OK',risk='NORMAL',events=list(rows))

class EventDateDisplay(unittest.TestCase):
    def test_future_day_is_not_displayed_as_today(self):
        text=next_event(news(event(datetime(2026,11,6,8,30,tzinfo=ET))),NOW)
        self.assertIn('Fri Nov 06 2026',text);self.assertIn('08:30 ET',text);self.assertNotIn('today',text)
    def test_same_day_is_explicit_and_remains_timed(self):
        text=next_event(news(event(datetime(2026,11,2,10,0,tzinfo=ET))),NOW)
        self.assertIn('today',text);self.assertIn('10:00 ET',text)
    def test_next_year_is_unambiguous(self):
        text=next_event(news(event(datetime(2027,1,4,8,30,tzinfo=ET))),datetime(2026,12,31,9,15,tzinfo=ET))
        self.assertIn('Mon Jan 04 2027',text)
    def test_utc_day_boundary_uses_et_day(self):
        now=datetime(2026,11,3,0,0,tzinfo=timezone.utc)
        text=next_event(news(event(datetime(2026,11,3,1,0,tzinfo=timezone.utc))),now)
        self.assertIn('today',text);self.assertIn('20:00 ET',text)
    def test_active_date_only_has_no_invented_release_time(self):
        day=event(datetime(2026,11,2,0,0,tzinfo=ET),date_only=True)
        text=next_event(news(day,event(datetime(2026,11,2,10,0,tzinfo=ET))),NOW)
        self.assertIn('today',text);self.assertIn('all-day ET',text);self.assertNotIn('00:00',text)
    def test_future_date_only_keeps_date_and_no_release_time(self):
        text=next_event(news(event(datetime(2026,11,6,0,0,tzinfo=ET),date_only=True)),NOW)
        self.assertIn('Fri Nov 06 2026',text);self.assertIn('all-day ET',text);self.assertNotIn('00:00',text)
    def test_past_timed_event_not_selected(self):
        text=next_event(news(event(datetime(2026,11,2,8,30,tzinfo=ET),'Past'),event(datetime(2026,11,6,8,30,tzinfo=ET),'Future')),NOW)
        self.assertIn('Future',text);self.assertNotIn('Past',text)
    def test_bad_or_unavailable_calendar_is_explicit(self):
        self.assertEqual(next_event(dict(quality='DATA_INCOMPLETE'),NOW),'event data unavailable')
        self.assertIn('invalid event time',next_event(news(dict(time_utc='2026-11-06T08:30:00')),NOW))
        self.assertIn('optional coverage incomplete',next_event(news(),NOW))
    def test_event_and_risk_inputs_are_not_mutated(self):
        value=news(event(datetime(2026,11,2,0,0,tzinfo=ET),date_only=True));value['risk']='HIGH';before=copy.deepcopy(value)
        next_event(value,NOW);self.assertEqual(value,before)
    def test_actual_premarket_formatter_stays_bounded_and_dated(self):
        text=premarket_text({},news(event(datetime(2026,11,6,8,30,tzinfo=ET))),NOW)
        self.assertEqual(len(text.splitlines()),8);self.assertLess(len(text),3500)
        self.assertIn('Fri Nov 06 2026',text);self.assertIn('Action: WAIT',text)
        self.assertIn('Premarket range: unavailable',text)

if __name__=='__main__':unittest.main()
