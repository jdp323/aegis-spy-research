import unittest,tempfile
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from core.storage import Store
from research.live_trend import evaluate,text_for
from core.bot_commands import execute

NOW=datetime(2026,10,6,15,0,10,tzinfo=timezone.utc)
class LiveTrendTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=Store(Path(self.temp.name)/'state.sqlite');self.addCleanup(self.store.close)
        self.quote={'provider':'alpaca-sip','symbol':'SPY','data_type':'quote','entitlement':'REALTIME','quality':'DATA_OK','source_timestamp':(NOW-timedelta(seconds=1)).isoformat(),'received_timestamp':NOW.isoformat(),'payload':{'bid':640,'ask':640.02}}
        self.store.put('quote:SPY',self.quote);self.store.put('stream:sip',{'state':'CONNECTED','at':NOW.isoformat()})
        end=NOW.replace(second=0);bars=[]
        for i in range(40):
            p=600+i;bars.append({'t':(end-timedelta(minutes=40-i)).isoformat(),'o':p,'h':p+1,'l':p-1,'c':p,'v':100})
        self.store.put('stream_bars:SPY',bars)
    def test_fresh_sip_quote_and_minute_history_yield_live_descriptive_trend(self):
        r=evaluate(self.store,NOW);self.assertEqual(r['status'],'LIVE_TREND');self.assertEqual(r['direction'],'UP');self.assertEqual(r['counts']['UP'],4)
        text=text_for(r,NOW);self.assertIn('age 1.0s',text);self.assertIn('BID $640.00',text);self.assertIn('not a fill',text);self.assertIn('not a forecast probability',text);self.assertIn('ONE-MINUTE BARS THROUGH:',text)
    def test_down_and_mixed_quote_relationships(self):
        bars=self.store.get('stream_bars:SPY')
        for i,b in enumerate(bars):b.update(o=640-i,h=641-i,l=639-i,c=640-i)
        self.store.put('stream_bars:SPY',bars);q={**self.quote,'payload':{'bid':599,'ask':599.02}};self.store.put('quote:SPY',q)
        self.assertEqual(evaluate(self.store,NOW)['direction'],'DOWN')
        self.store.put('quote:SPY',{**q,'payload':{'bid':650,'ask':650.02}})
        self.assertEqual(evaluate(self.store,NOW)['direction'],'MIXED')
    def test_stale_and_future_quote_are_never_live(self):
        for seconds in (6,-1):
            self.store.put('quote:SPY',{**self.quote,'source_timestamp':(NOW-timedelta(seconds=seconds)).isoformat()})
            self.assertEqual(evaluate(self.store,NOW)['status'],'UNAVAILABLE')
    def test_stale_receipt_is_rejected(self):
        self.store.put('quote:SPY',{**self.quote,'received_timestamp':(NOW-timedelta(seconds=6)).isoformat()})
        self.assertEqual(evaluate(self.store,NOW)['status'],'UNAVAILABLE')
    def test_public_iex_or_wrong_symbol_never_promoted_to_sip(self):
        for change in ({'provider':'yahoo-public'},{'provider':'alpaca-iex'},{'symbol':'QQQ'},{'entitlement':'DELAY_UNVERIFIED'},{'quality':'DATA_STALE'}):
            self.store.put('quote:SPY',{**self.quote,**change});self.assertEqual(evaluate(self.store,NOW)['status'],'UNAVAILABLE')
    def test_disconnected_stale_and_unconfigured_stream_block(self):
        for health in ({'state':'FEED_NOT_CONFIGURED'},{'state':'FEED_DISCONNECTED','at':NOW.isoformat()},{'state':'CONNECTED','at':(NOW-timedelta(seconds=31)).isoformat()}):
            self.store.put('stream:sip',health);self.assertEqual(evaluate(self.store,NOW)['status'],'UNAVAILABLE')
    def test_bad_bid_ask_or_timestamp_rejected(self):
        for change in ({'payload':{'bid':641,'ask':640}},{'payload':{'bid':True,'ask':640}},{'source_timestamp':'2026-10-06T15:00:00'}):
            self.store.put('quote:SPY',{**self.quote,**change});self.assertEqual(evaluate(self.store,NOW)['status'],'UNAVAILABLE')
    def test_warmup_does_not_fabricate_ratio(self):
        self.store.put('stream_bars:SPY',self.store.get('stream_bars:SPY')[-30:]);r=evaluate(self.store,NOW)
        self.assertEqual(r['status'],'LIVE_QUOTE_ONLY');self.assertNotIn('INDICATOR SUPPORT',text_for(r,NOW))
    def test_connected_iex_bars_cannot_replace_missing_or_stale_quote(self):
        # Mirrors an authenticated bar-only feed: sufficient history is not bid/ask.
        self.store.put('quote:SPY',None)
        self.store.put('research_stream_bars:SPY:iex',self.store.get('stream_bars:SPY'))
        self.store.put('stream:iex',{'state':'CONNECTED','at':NOW.isoformat()})
        for quote in (None,{**self.quote,'provider':'alpaca-iex','source_timestamp':(NOW-timedelta(seconds=6)).isoformat()}):
            with self.subTest(quote_present=quote is not None):
                self.store.put('research_quote:SPY:iex',quote)
                result=evaluate(self.store,NOW)
                self.assertEqual(result['status'],'UNAVAILABLE');self.assertIsNone(result['direction'])
                self.assertNotIn('counts',result);self.assertNotIn('mid',result)
                self.assertTrue(text_for(result,NOW).startswith('REAL-TIME: UNAVAILABLE'))
    def test_bar_only_feed_cannot_create_proxy_entry_or_promote_live_gate(self):
        from backtesting.proxy_engine import candidate
        from core.upgrade_service import read_config
        self.store.put('quote:SPY',None)
        self.store.put('research_stream_bars:SPY:iex',self.store.get('stream_bars:SPY'))
        self.store.put('stream:iex',{'state':'CONNECTED','at':NOW.isoformat()})
        signal,quote,rows=candidate(self.store,{'quality':'DATA_OK','risk':'NORMAL'},read_config(),NOW)
        self.assertGreaterEqual(len(rows),31)
        self.assertFalse(signal.paper_eligible);self.assertFalse(signal.actionable);self.assertFalse(signal.live_signal_ready)
        self.assertIn('PROXY_FRESH_FEED_AND_31_BAR_TAIL_REQUIRED',signal.paper_blockers)
        self.assertIsNone(signal.spy_price);self.assertFalse(quote)
    def test_gap_resets_warmup(self):
        rows=self.store.get('stream_bars:SPY');del rows[-3];self.store.put('stream_bars:SPY',rows)
        self.assertEqual(evaluate(self.store,NOW)['status'],'LIVE_QUOTE_ONLY')
    def test_invalid_or_unordered_history_never_establishes_trend(self):
        rows=self.store.get('stream_bars:SPY');original=[dict(x) for x in rows]
        rows[-1]['c']=float('inf')
        # JSON state itself rejects nonfinite numbers; adversarial payload via read mock.
        with patch.object(self.store,'get',side_effect=lambda key:rows if key=='stream_bars:SPY' else {'quote:SPY':self.quote,'stream:sip':{'state':'CONNECTED','at':NOW.isoformat()}}.get(key)):
            self.assertEqual(evaluate(self.store,NOW)['status'],'LIVE_QUOTE_ONLY')
        self.store.put('stream_bars:SPY',original[::-1]);self.assertEqual(evaluate(self.store,NOW)['status'],'LIVE_QUOTE_ONLY')
    def test_stale_minute_history_never_current_trend(self):
        rows=self.store.get('stream_bars:SPY')
        for b in rows:b['t']=(datetime.fromisoformat(b['t'])-timedelta(minutes=3)).isoformat()
        self.store.put('stream_bars:SPY',rows);self.assertEqual(evaluate(self.store,NOW)['status'],'LIVE_QUOTE_ONLY')
    def test_closed_and_early_close_session_not_live_regular(self):
        for now in (NOW.replace(hour=21),NOW.replace(month=11,day=27,hour=18)):
            self.assertEqual(evaluate(self.store,now)['status'],'UNAVAILABLE')
    def test_command_rechecks_live_state_after_public_fetch_and_labels_history(self):
        unavailable={'status':'UNAVAILABLE','reason':'Feed not configured','direction':None}
        with patch('core.bot_commands.Store',return_value=self.store),patch.object(self.store,'close'),patch('research.live_trend.evaluate',return_value=unavailable) as check,patch('research.basic_trend.on_demand_text',return_value='SPY TREND: UP | PREMARKET'):
            text=execute({'command':'trend','text':'details','tenant':'owner'})
        self.assertEqual(check.call_count,2);self.assertTrue(text.startswith('REAL-TIME: UNAVAILABLE'));self.assertIn('SPY HISTORICAL BAR TREND:',text)
    def test_live_command_does_not_fetch_public_fallback(self):
        live=evaluate(self.store,NOW)
        with patch('core.bot_commands.Store',return_value=self.store),patch.object(self.store,'close'),patch('research.live_trend.evaluate',return_value=live),patch('research.basic_trend.on_demand_text') as fallback:
            self.assertIn('LIVE-QUOTE TREND: UP',execute({'command':'trend','text':'details','tenant':'0'*24}));fallback.assert_not_called()

if __name__=='__main__':unittest.main()
