import unittest,tempfile,copy,json,hashlib,os,urllib.error,ssl
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from tests.test_research_alerts import fixture,NOW,SOURCE
from data.secondary_spy import collect,refresh,parse_daily,URL
from data.massive_research import MassiveResearchProvider,SOURCE as MASSIVE
from research.source_consensus import daily_context,compare_intraday,message_context
from monitoring.research_alerts import observe,changes,context,text_for
from core.sessions import market_session,ET

class IndependentSources(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
    def daily(self,down=False):
        days=[];d=NOW.astimezone(ET).date()-timedelta(days=1)
        while len(days)<75:
            if market_session(datetime.combine(d,datetime.min.time(),ET)+timedelta(hours=12))['active']:days.append(d)
            d-=timedelta(days=1)
        lines=['Date,Open,High,Low,Close,Volume']
        for i,d in enumerate(reversed(days)):
            c=600-i if down else 500+i
            lines.append(f'{d.isoformat()},{c},{c+1},{c-1},{c},10000')
        raw=('\n'.join(lines)+'\n').encode()
        with patch('data.secondary_spy.ROOT',self.root):doc=collect(NOW,lambda:raw)
        return doc,raw
    def test_independent_daily_up_and_down_and_warmup(self):
        for down,trend in ((False,'UPWARD'),(True,'DOWNWARD')):
            doc,_=self.daily(down);d=daily_context(doc,NOW,self.root)
            self.assertEqual(d['trend'],trend);self.assertEqual(d['status'],'DAILY_RESEARCH_ONLY');self.assertIsNotNone(d['rsi14']);self.assertEqual(d['action'],'NO TRADE')
    def test_tampered_digest_and_rows_rejected(self):
        doc,_=self.daily();doc['rows'][-1]['close']+=1
        self.assertEqual(daily_context(doc,NOW,self.root)['status'],'UNAVAILABLE')
        doc,_=self.daily();(self.root/'data/public_cache'/(doc['sha256']+'.csv')).write_text('tampered')
        self.assertEqual(daily_context(doc,NOW,self.root)['status'],'UNAVAILABLE')
    def test_stale_and_missing_final_session_rejected(self):
        doc,_=self.daily();self.assertEqual(daily_context(doc,NOW+timedelta(days=2),self.root)['reason'],'DAILY_FETCH_STALE')
        doc,_=self.daily();doc['rows'].pop();self.assertEqual(daily_context(doc,NOW,self.root)['status'],'UNAVAILABLE')
    def test_current_day_partial_bar_is_excluded(self):
        doc,raw=self.daily();raw+=b'2026-10-05,100,101,99,100,100\n'
        with patch('data.secondary_spy.ROOT',self.root):doc=collect(NOW,lambda:raw)
        d=daily_context(doc,NOW,self.root);self.assertEqual(d['as_of_date'],'2026-10-02');self.assertEqual(d['trend'],'UPWARD')
    def test_missing_session_in_indicator_window_rejected(self):
        doc,raw=self.daily();lines=raw.splitlines();del lines[-10];raw=b'\n'.join(lines)+b'\n'
        with patch('data.secondary_spy.ROOT',self.root):doc=collect(NOW,lambda:raw)
        self.assertEqual(daily_context(doc,NOW,self.root)['reason'],'DAILY_HISTORY_GAP_OR_CALENDAR_UNAVAILABLE')
    def test_failed_daily_request_not_retried_same_day(self):
        calls=[]
        def fail():calls.append(1);raise OSError('offline')
        with patch('data.secondary_spy.ROOT',self.root):
            a=refresh(NOW,fail);b=refresh(NOW+timedelta(hours=1),fail)
        self.assertEqual(len(calls),1);self.assertEqual(a,b);self.assertEqual(a['rows'],[])
    def test_intraday_prices_only_compared_same_recent_timestamp(self):
        a=fixture();b=fixture();b['source']=MASSIVE
        self.assertEqual(compare_intraday(a,b,NOW)['status'],'AGREEMENT')
        b['levels']['last_close']=620;self.assertEqual(compare_intraday(a,b,NOW)['status'],'DISAGREEMENT')
        b['levels']['last_completed_bar_at']=(NOW-timedelta(minutes=10)).isoformat();self.assertEqual(compare_intraday(a,b,NOW)['status'],'NOT_COMPARABLE')
        b=fixture();b['source']=MASSIVE;self.assertEqual(compare_intraday(a,b,NOW+timedelta(hours=1))['status'],'NOT_COMPARABLE')
    def test_disagreement_blocks_direction_and_no_price(self):
        raw=fixture();raw['multi_source']={'intraday_comparison':{'status':'DISAGREEMENT'}}
        o=observe(raw,market_session(NOW),NOW);self.assertEqual(o['reason'],'SOURCE_DISAGREEMENT');self.assertNotIn('$',text_for(o,market_session(NOW),NOW))
    def test_source_switch_not_mistaken_for_price_move(self):
        old=context(observe(fixture(),market_session(NOW),NOW));later=NOW+timedelta(minutes=10);raw=fixture(later);raw['source']=MASSIVE
        o=observe(raw,market_session(later),later);self.assertEqual(o['quality'],'PUBLIC_RESEARCH_ONLY');self.assertEqual(changes(o,old,market_session(later)),[])
        self.assertIn('Massive API bars',text_for(o,market_session(later),later))
    def test_horizon_conflict_is_explicit(self):
        doc,_=self.daily(True);d=daily_context(doc,NOW,self.root)
        self.assertIn('horizons conflict',message_context({'multi_source':{'daily':d}},'UPWARD 5m STRUCTURE'))
    def massive(self,**mutations):
        doc={'ticker':'SPY','status':'OK','adjusted':False,'results':[{'t':int((NOW-timedelta(minutes=5)).timestamp()*1000),'o':600,'h':602,'l':599,'c':601,'v':1000}]};doc.update(mutations)
        return MassiveResearchProvider(lambda path,params:doc,lambda:NOW)
    def test_massive_not_configured_no_network_or_secret(self):
        with patch.dict(os.environ,{},clear=True),patch('urllib.request.urlopen') as network:
            p=MassiveResearchProvider();self.assertEqual(p.get_bars().quality,'FEED_NOT_CONFIGURED');network.assert_not_called()
    def test_massive_completed_raw_bars_research_only(self):
        p=self.massive();d=p.get_bars();self.assertEqual(d.payload['bars'][0]['close'],601);self.assertEqual(d.entitlement,'DELAY_UNVERIFIED');self.assertNotEqual(d.quality,'DATA_OK')
        self.assertEqual(p.get_option_chain().payload,{})
    def test_massive_wrong_symbol_adjusted_or_partial_chain_rejected(self):
        for kwargs in ({'ticker':'QQQ'},{'adjusted':True},{'next_url':'https://untrusted.invalid'},{'results':[]}):
            d=self.massive(**kwargs).get_bars();self.assertEqual(d.payload,{})
    def test_massive_rate_limit_and_auth_cooldown(self):
        for code in (429,403):
            calls=[]
            def fail(path,params):calls.append(1);raise urllib.error.HTTPError('https://api.massive.com',code,'',{},None)
            p=MassiveResearchProvider(fail,lambda:NOW);p.get_bars();p.get_bars();self.assertEqual(len(calls),1);self.assertGreater(p.health()['retry_after_seconds'],0)
    def test_hub_independent_daily_and_explicit_failover(self):
        from data.research_hub import enrich
        from core.spy_research import analyze
        p=self.massive();primary={'data_status':'PUBLIC_SOURCE_UNAVAILABLE','source':SOURCE,'levels':None}
        with patch('data.research_hub.ROOT',self.root),patch('data.research_hub.refresh',return_value={}),patch('data.research_hub.daily_context',return_value={'status':'UNAVAILABLE'}):
            (self.root/'research').mkdir(exist_ok=True);r=enrich(primary,analyze,NOW,p)
        self.assertEqual(r['source'],MASSIVE);self.assertEqual(r['multi_source']['failover'],'EXPLICIT_PUBLIC_RESEARCH_FALLBACK');self.assertFalse(r['signal_ready'])
    def test_verified_windows_tls_fallback_does_not_disable_checks(self):
        from data.public_https import download
        from types import SimpleNamespace
        failure=urllib.error.URLError(ssl.SSLCertVerificationError('fixture trusted OS CA'))
        with patch('data.public_https.os.name','nt'),patch('data.public_https.urllib.request.urlopen',side_effect=failure),patch('data.public_https.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout=b'fixture')) as run:
            body,transport=download(URL)
        self.assertEqual(body,b'fixture');self.assertEqual(transport,'WINDOWS_OS_VERIFIED_TLS');args=run.call_args.args[0];self.assertNotIn('-k',args);self.assertNotIn('--insecure',args);self.assertIn('--proto',args)
    def test_http_denial_does_not_trigger_alternate_transport(self):
        from data.public_https import download
        with patch('data.public_https.urllib.request.urlopen',side_effect=urllib.error.HTTPError(URL,403,'denied',{},None)),patch('data.public_https.subprocess.run') as run:
            with self.assertRaises(urllib.error.HTTPError):download(URL)
            run.assert_not_called()
    def test_public_downloader_rejects_arbitrary_urls(self):
        from data.public_https import download
        with self.assertRaises(ValueError):download('https://untrusted.invalid')

if __name__=='__main__':unittest.main()
