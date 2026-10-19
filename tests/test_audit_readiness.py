import tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from core.storage import Store
from core.upgrade_service import Watchdog
from core.feed_health import text_for

NOW=datetime(2026,10,6,14,tzinfo=timezone.utc)
class ReadinessAuditTests(unittest.TestCase):
    def test_iex_arrival_prevents_false_no_data_warning_without_promoting_sip(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        if folder:
            store=Store(Path(folder.name)/'db.sqlite');self.addCleanup(store.close)
            w=Watchdog(store);session={'active':True,'date':'2026-10-06'}
            self.assertFalse(w.check(session,NOW))
            store.put('last_market:iex',{'source_timestamp':(NOW+timedelta(seconds=590)).isoformat()})
            self.assertFalse(w.check(session,NOW+timedelta(seconds=600)))
            self.assertIsNone(store.get('last_market:sip'))
            self.assertTrue(w.check(session,NOW+timedelta(seconds=1190)))
            self.assertFalse(w.check(session,NOW+timedelta(seconds=1200)))
    def test_future_or_malformed_arrivals_do_not_suppress_warning(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        if folder:
            store=Store(Path(folder.name)/'db.sqlite');self.addCleanup(store.close)
            w=Watchdog(store);session={'active':True,'date':'2026-10-06'}
            w.check(session,NOW)
            store.put('last_market:sip',{'source_timestamp':'invalid'})
            store.put('last_market:iex',{'source_timestamp':(NOW+timedelta(days=1)).isoformat()})
            self.assertTrue(w.check(session,NOW+timedelta(seconds=600)))
    def test_configuration_never_implies_live_data_and_idle_never_implies_opra(self):
        data={'provider':{'status':'DATA_OK'},'session':{'state':'REGULAR'},'streams':{'iex':{'state':'CONNECTED_IDLE','at':NOW.isoformat()},'opra':{'state':'IDLE_NO_CONTRACT_SUBSCRIPTIONS','at':NOW.isoformat()}},'live_trend':{'status':'UNAVAILABLE','reason':'stale quote'}}
        text=text_for(data,NOW)
        self.assertIn('DATA_OK (configuration only)',text)
        self.assertIn('no verified quote timestamp',text)
        self.assertIn('Idle option subscriptions do not prove entitlement',text)
        self.assertIn('UNAVAILABLE — stale quote',text)
        self.assertNotIn('Live feed: DATA_OK',text)
    def test_old_quote_and_stale_heartbeat_are_visible(self):
        old=(NOW-timedelta(minutes=10)).isoformat()
        data={'streams':{'iex':{'state':'CONNECTED','at':old}},'research_underlying':{'quality':'DATA_STALE','source_timestamp':old}}
        text=text_for(data,NOW)
        self.assertIn('heartbeat stale',text);self.assertIn('age 600.0s',text)
        self.assertIn('DATA_STALE',text)
if __name__=='__main__':unittest.main()
