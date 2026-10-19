import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime,timezone,timedelta
from core.storage import Store
from data.stream import Stream
from research.live_trend import evaluate,text_for

NOW=datetime(2026,10,6,15,0,10,tzinfo=timezone.utc)
class FrozenClock(datetime):
    @classmethod
    def now(cls,tz=None):return NOW if tz else NOW.replace(tzinfo=None)
class IexResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=Store(Path(self.temp.name)/'test.sqlite');self.addCleanup(self.store.close)
        self.stream=Stream(self.store,feed='iex')
    def seed(self):
        with patch('data.stream.iso',return_value=NOW.isoformat()),patch('data.models.datetime',FrozenClock):
            end=NOW.replace(second=0)
            for i in range(40):
                p=600+i
                self.assertTrue(self.stream.ingest({'T':'b','S':'SPY','t':(end-timedelta(minutes=40-i)).isoformat(),'o':p,'h':p+1,'l':p-1,'c':p,'v':100}))
            self.assertTrue(self.stream.ingest({'T':'q','S':'SPY','t':(NOW-timedelta(seconds=1)).isoformat(),'bp':640,'ap':640.02}))
    def test_iex_quote_and_history_are_isolated_from_core_sip_risk_inputs(self):
        self.seed()
        for key in ('quote:SPY','stream_bars:SPY','stream_bar:SPY','trade:SPY'):self.assertIsNone(self.store.get(key))
        self.assertEqual(self.store.get('research_quote:SPY:iex')['provider'],'alpaca-iex')
        self.assertEqual(len(self.store.get('research_stream_bars:SPY:iex')),40)
    def test_iex_is_an_explicit_live_research_fallback(self):
        self.seed();self.store.put('stream:sip',{'state':'FEED_NOT_CONFIGURED'})
        r=evaluate(self.store,NOW);self.assertEqual(r['status'],'LIVE_TREND');self.assertEqual(r['direction'],'UP');self.assertEqual(r['coverage'],'SINGLE_EXCHANGE_IEX')
        text=text_for(r,NOW);self.assertIn('SINGLE EXCHANGE',text);self.assertIn('not consolidated NBBO',text);self.assertIn('SIP unavailable:',text);self.assertIn('age 1.0s',text)
    def test_valid_sip_takes_precedence_without_mixing_histories(self):
        self.seed();iex=self.store.get('research_quote:SPY:iex')
        self.store.put('quote:SPY',{**iex,'provider':'alpaca-sip'});self.store.put('stream:sip',{'state':'CONNECTED','at':NOW.isoformat()})
        self.store.put('stream_bars:SPY',[])
        r=evaluate(self.store,NOW);self.assertEqual(r['provider'],'alpaca-sip');self.assertEqual(r['status'],'LIVE_QUOTE_ONLY')
    def test_stale_iex_quote_cannot_replace_unavailable_sip(self):
        self.seed();self.assertEqual(evaluate(self.store,NOW+timedelta(seconds=5))['status'],'UNAVAILABLE')
    def test_sip_history_cannot_warm_iex_indicators(self):
        self.seed();self.store.put('stream_bars:SPY',self.store.get('research_stream_bars:SPY:iex'));self.store.put('research_stream_bars:SPY:iex',[])
        self.assertEqual(evaluate(self.store,NOW)['status'],'LIVE_QUOTE_ONLY')
    def test_unsupported_or_options_iex_feed_rejected(self):
        for args in ({'feed':'delayed_sip'},{'feed':'iex','options':True}):
            with self.assertRaises(ValueError):Stream(self.store,**args)
    def test_each_command_analysis_is_recomputed_from_latest_quote(self):
        self.seed();a=evaluate(self.store,NOW)
        q=self.store.get('research_quote:SPY:iex');q['payload']={'bid':500,'ask':500.02};self.store.put('research_quote:SPY:iex',q)
        b=evaluate(self.store,NOW);self.assertEqual(a['direction'],'UP');self.assertEqual(b['direction'],'MIXED');self.assertNotEqual(a['mid'],b['mid'])

if __name__=='__main__':unittest.main()
