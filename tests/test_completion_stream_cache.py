import contextlib,io,json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from core.storage import Store
from data.stream import Stream
from ops import supervisor

class CacheIntegrity(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'a.sqlite')
        self.now=datetime.now(timezone.utc);self.s=Stream(self.store,feed='iex',max_future_skew_seconds=2)
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def q(self,dt=None,**fields):return {'T':'q','S':'SPY','t':(dt or self.now).isoformat(),'bp':500,'ap':500.02,**fields}
    def test_invalid_new_quote_cannot_erase_good_cache(self):
        self.assertTrue(self.s.ingest(self.q()))
        before=self.store.get('research_quote:SPY:iex')
        self.assertFalse(self.s.ingest(self.q(self.now+timedelta(milliseconds=5),bp=-1)))
        self.assertEqual(before,self.store.get('research_quote:SPY:iex'))
    def test_restart_watermark_prevents_older_or_duplicate_replacement(self):
        self.assertTrue(self.s.ingest(self.q()))
        restarted=Stream(self.store,feed='iex')
        self.assertFalse(restarted.ingest(self.q(self.now-timedelta(seconds=1))))
        self.assertFalse(restarted.ingest(self.q()))
        self.assertEqual(self.now.isoformat(),self.store.get('research_quote:SPY:iex')['source_timestamp'])
    def test_signed_accepted_skew_is_not_clamped_watermark(self):
        future=self.now+timedelta(seconds=.5)
        self.assertTrue(self.s.ingest(self.q(future)))
        self.assertEqual(future,self.s.last_source[('SPY','q')])
        self.assertFalse(self.s.ingest(self.q(self.now)))
    def test_future_rejected_without_cache_or_watchdog(self):
        self.assertFalse(self.s.ingest(self.q(self.now+timedelta(seconds=10))))
        self.assertIsNone(self.store.get('research_quote:SPY:iex'))
        self.assertIsNone(self.store.get('last_market:iex'))
    def test_feed_watermarks_separate(self):
        self.assertTrue(self.s.ingest(self.q()))
        sip=Stream(self.store,feed='sip')
        self.assertTrue(sip.ingest(self.q(self.now-timedelta(seconds=1))))
        self.assertEqual('alpaca-sip',self.store.get('quote:SPY')['provider'])
    def test_updated_bar_same_minute_revises_but_does_not_duplicate(self):
        bar={'T':'b','S':'SPY','t':self.now.isoformat(),'o':500,'h':502,'l':499,'c':501,'v':1}
        self.assertTrue(self.s.ingest(bar));self.assertFalse(self.s.ingest(bar))
        self.assertTrue(self.s.ingest({**bar,'T':'u','v':2}))
        self.assertEqual(1,len(self.store.get('research_stream_bars:SPY:iex')))
        self.assertEqual(2,self.store.get('research_stream_bars:SPY:iex')[0]['v'])

class SupervisorCLI(unittest.TestCase):
    def test_unknown_args_and_help_never_start(self):
        with patch.object(supervisor,'start') as start,patch.object(supervisor,'run') as run:
            with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as error:supervisor.main(['typo'])
            self.assertEqual(2,error.exception.code);start.assert_not_called();run.assert_not_called()
            with contextlib.redirect_stdout(io.StringIO()),self.assertRaises(SystemExit):supervisor.main(['--help'])
            start.assert_not_called();run.assert_not_called()
    def test_no_argument_is_status(self):
        with patch.object(supervisor,'status',return_value={'read_only':True}) as status,patch.object(supervisor,'start') as start,contextlib.redirect_stdout(io.StringIO()):supervisor.main([])
        status.assert_called_once();start.assert_not_called()
    def test_status_read_only_allowlisted(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'runtime').mkdir();f=p/'runtime/services.json'
            f.write_text(json.dumps({'at':'2026-10-17T00:00:00Z','components':{},'private':'DO_NOT_EXPORT'}))
            before={str(q):q.read_bytes() for q in p.rglob('*') if q.is_file()}
            result=supervisor.status(p,clock=lambda:datetime(2026,10,17,tzinfo=timezone.utc),probe=False)
            self.assertTrue(result['read_only']);self.assertNotIn('DO_NOT_EXPORT',json.dumps(result))
            self.assertEqual(before,{str(q):q.read_bytes() for q in p.rglob('*') if q.is_file()})

if __name__=='__main__':unittest.main()
