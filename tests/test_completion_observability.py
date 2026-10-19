import json,sqlite3,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from monitoring.trend_evidence import record
from ops.day_simulation import MemoryStore
from core.sessions import ET,market_session
from ops.live_verify import scheduled
from backtesting.idea_tracker import IdeaTracker

class EvidenceTests(unittest.TestCase):
    def test_append_only_signed_status_and_duplicate_reservation(self):
        now=datetime(2026,10,19,10,15,tzinfo=ET)
        ctx={'reason':'source stale','failed_predicate':'SOURCE_TOO_OLD','feed_quality':'IEX','features':{},'bar_research':{'reason':None},'diagnostics':[{'provider':'alpaca-iex','source_age_seconds':7.2,'receipt_age_seconds':-.1}]}
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'o.sqlite';r=record(p,'v5-trend-fixture',now,ctx,{'quality':'DATA_OK'})
            self.assertEqual('DESCRIPTIVE_ONLY',r['status']);self.assertEqual(-.1,r['quote_diagnostics'][0]['receipt_age_seconds'])
            record(p,'v5-trend-fixture',now+timedelta(seconds=1),ctx,{})
            db=sqlite3.connect(p);self.assertEqual(1,db.execute('SELECT count(*) FROM trend_status_events').fetchone()[0])
            with self.assertRaises(sqlite3.IntegrityError):db.execute('UPDATE trend_status_events SET at=?',('bad',))
            db.close()
            with self.assertRaises(ValueError):record(p,'bad',now,dict(ctx,feed_quality='SIMULATED'),{})
    def test_next_session_verification_not_disabled_by_old_completed_day(self):
        store=MemoryStore();store.put('live_verify_deployment',{'completed':True,'date':'2026-10-16'})
        now=datetime(2026,10,19,9,35,tzinfo=ET)
        with patch('ops.live_verify.sample') as sample:scheduled(store,now);sample.assert_called_once()
        store.put('live_verify_deployment',{'completed':True,'date':'2026-10-19'})
        with patch('ops.live_verify.sample') as sample:scheduled(store,now);sample.assert_not_called()
    def test_naive_clocks_rejected_and_unknown_year_closed(self):
        with self.assertRaises(ValueError):market_session(datetime(2026,10,19,10))
        self.assertEqual('CALENDAR_REFRESH_REQUIRED',market_session(datetime(2028,1,3,tzinfo=ET))['reason'])
    def test_entry_deadline_refused_without_registering_or_closing_position(self):
        from tests.test_v5_ideas import seed,oq,NOW
        tracker=IdeaTracker(simulation=True);i=seed();i['max_hold_until']=NOW.isoformat()
        with self.assertRaisesRegex(ValueError,'DEADLINE'):tracker.register(i,oq(),NOW)
        self.assertFalse(tracker.positions())
        i=seed();i['signal_expiry']=(NOW+timedelta(hours=2)).isoformat()
        with self.assertRaisesRegex(ValueError,'VALIDITY'):tracker.register(i,oq(),NOW)
        self.assertFalse(tracker.positions())

if __name__=='__main__':unittest.main()
