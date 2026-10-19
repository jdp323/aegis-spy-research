import tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from core.storage import Store
from data.stream import Stream

class StreamPayloadTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.store=Store(Path(self.folder.name)/'fixture.sqlite');self.addCleanup(self.store.close)
        self.stream=Stream(self.store);self.now=datetime.now(timezone.utc)
        self.clock=patch('data.stream.iso',return_value=self.now.isoformat());self.clock.start();self.addCleanup(self.clock.stop)
        self.bar={'T':'b','S':'SPY','t':self.now.isoformat(),'o':600.,'h':602.,'l':599.,'c':601.,'v':100,'vw':600.5}
    def test_invalid_bars_do_not_reset_watchdog_or_store_history(self):
        for change in ({'c':float('nan')},{'o':True},{'h':598},{'l':603},{'v':-1},{'v':'100'},{'vw':float('inf')}):
            with self.subTest(change=change):
                self.assertFalse(self.stream.ingest({**self.bar,**change}))
                self.assertIsNone(self.store.get('last_market:sip'))
                self.assertIsNone(self.store.get('stream_bars:SPY'))
                self.assertIsNone(self.store.get('stream_bar:SPY'))
                self.assertEqual(self.stream.last_source,{})
    def test_invalid_newer_bar_does_not_block_valid_earlier_bar(self):
        self.assertFalse(self.stream.ingest({**self.bar,'c':-1}))
        valid={**self.bar,'t':(self.now-timedelta(seconds=1)).isoformat()}
        self.assertTrue(self.stream.ingest(valid));self.assertEqual(self.store.get('stream_bars:SPY'),[valid])
    def test_invalid_trade_does_not_advance_watermark(self):
        self.assertFalse(self.stream.ingest({'T':'t','S':'SPY','t':self.now.isoformat(),'p':-1}))
        self.assertTrue(self.stream.ingest({'T':'t','S':'SPY','t':(self.now-timedelta(seconds=1)).isoformat(),'p':600}))
    def test_stale_bar_is_archived_without_watchdog_recovery(self):
        self.assertTrue(self.stream.ingest({**self.bar,'t':(self.now-timedelta(minutes=2)).isoformat()}))
        self.assertIsNone(self.store.get('last_market:sip'));self.assertEqual(len(self.store.get('stream_bars:SPY')),1)
    def test_valid_update_replaces_same_timestamp_and_refreshes_health(self):
        self.assertTrue(self.stream.ingest(self.bar))
        self.assertTrue(self.stream.ingest({**self.bar,'T':'u','c':601.5}))
        self.assertEqual(len(self.store.get('stream_bars:SPY')),1)
        self.assertEqual(self.store.get('stream_bars:SPY')[0]['c'],601.5)
        self.assertIsNotNone(self.store.get('last_market:sip'))
    def test_non_object_and_non_string_symbol_fail_closed(self):
        for bad in (None,[],42,'bar',{'T':'b','S':[]},{'T':'b','S':{}}):self.assertFalse(self.stream.ingest(bad))

if __name__=='__main__':unittest.main()
