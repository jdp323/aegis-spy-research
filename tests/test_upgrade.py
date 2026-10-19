import unittest,tempfile,json,sqlite3,math,asyncio,os
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from data.models import quote,Datum,Quality
from data.providers import AlpacaProvider,ProviderRouter,UnconfiguredProvider
from core.storage import Store
from core.sessions import market_session
from features.indicators import normalize,resample,calculate,multi_timeframe
from features.market_regime import classify
from options.contract_selector import select,expected_move
from core.signals import Signal,tier,build
from monitoring.position_monitor import review
from core.upgrade_service import Watchdog,fresh
from backtesting.paper_engine import PaperEngine
from news.engine import NewsProvider
from ops.backup import backup,restore
NOW=datetime(2026,10,5,15,0,tzinfo=timezone.utc)
def q(symbol='SPY',bid=600,ask=600.1,now=NOW):return quote('alpaca-opra' if symbol!='SPY' else 'alpaca-sip',symbol,{'bp':bid,'ap':ask,'t':now.isoformat()},received=now.isoformat()).view(now)
def chain(now=NOW):return {'SPY261009C00600000':{'latestQuote':{'bp':2.0,'ap':2.1,'t':now.isoformat()},'greeks':{'delta':.5,'gamma':.01,'theta':-.05,'vega':.1},'impliedVolatility':.2,'volume':1000,'openInterest':2000}}
def bars(count=240):
    t=datetime(2026,10,5,13,30,tzinfo=timezone.utc)
    return [{'t':(t+timedelta(minutes=i)).isoformat(),'o':600+i*.01,'h':601+i*.01,'l':599+i*.01,'c':600.5+i*.01,'v':100+i} for i in range(count)]
class UpgradeTests(unittest.TestCase):
    def test_quality_ages_and_future(self):
        d=quote('fixture','SPY',{'bp':1,'ap':2,'t':NOW.isoformat()},received=NOW.isoformat())
        self.assertEqual(d.view(NOW+timedelta(seconds=16))['quality'],Quality.STALE)
        self.assertEqual(d.view(NOW-timedelta(seconds=1))['quality'],Quality.INVALID)
        self.assertEqual(quote('fixture','SPY',{'bp':3,'ap':2,'t':NOW.isoformat()}).quality,Quality.INVALID)
    def test_router_does_not_downgrade(self):
        r=ProviderRouter(UnconfiguredProvider());v,attempts=r.request('get_underlying_quote','SPY');self.assertNotEqual(v['quality'],Quality.OK);self.assertEqual(len(attempts),3)
    def test_adapter_no_credentials(self):
        with patch.dict(os.environ,{},clear=True):self.assertEqual(AlpacaProvider().get_underlying_quote().quality,Quality.UNCONFIGURED)
    def test_entitlement_explicit_and_pagination(self):
        calls=[]
        def transport(path,params):
            calls.append((path,params.copy()))
            return {'snapshots':chain(),'next_page_token':'two'} if len(calls)==1 else {'snapshots':{},'next_page_token':None}
        d=AlpacaProvider(transport).get_option_chain();self.assertEqual(len(calls),2);self.assertTrue(all(x[1]['feed']=='opra' for x in calls));self.assertTrue(d.payload['complete'])
    def test_session_states(self):
        for hour,minute,expected in [(12,0,'PREMARKET'),(13,35,'OPENING'),(15,0,'REGULAR'),(19,45,'CLOSING'),(21,0,'AFTER_HOURS')]:self.assertEqual(market_session(NOW.replace(hour=hour,minute=minute))['state'],expected)
        self.assertEqual(market_session(datetime(2026,11,27,16,tzinfo=timezone.utc))['state'],'EARLY_CLOSE')
        self.assertEqual(market_session(datetime(2026,12,25,16,tzinfo=timezone.utc))['state'],'HOLIDAY')
        self.assertTrue(market_session(datetime(2027,1,4,16,tzinfo=timezone.utc))['active'])
        self.assertFalse(market_session(datetime(2028,1,4,16,tzinfo=timezone.utc))['active'])
    def test_no_future_or_partial_bars(self):
        b=normalize(bars(),now=NOW);self.assertEqual(len(b),90);self.assertEqual(len(resample(b,5)),18)
        missing=b[:3]+b[4:];self.assertEqual(len(resample(missing,5)),17)
        self.assertIsNone(calculate(b)['ema200']);self.assertIsNone(calculate(b[:10])['atr14'])
        self.assertEqual(calculate(b)['rsi14'],100)
    def test_future_mutation_no_lookahead(self):
        raw=bars();a=multi_timeframe(raw,now=NOW);raw[-1].update(o=900,h=901,l=899,c=900);self.assertEqual(a,multi_timeframe(raw,now=NOW))
    def test_invalid_ohlc_rejected(self):
        b=bars(10);b[0]['c']=float('nan')
        with self.assertRaises(ValueError):normalize(b,now=NOW)
    def test_insufficient_regime(self):self.assertEqual(classify(calculate(normalize(bars(10),now=NOW)))['regime'],'UNSAFE')
    def test_selector_missing_liquidity_and_zero_dte(self):
        self.assertIsNotNone(select(chain(),600,'CALL',NOW)['best_contract']);c=chain();del next(iter(c.values()))['openInterest'];self.assertIsNone(select(c,600,'CALL',NOW)['best_contract'])
        c={'SPY261005C00600000':next(iter(chain().values()))};self.assertIsNone(select(c,600,'CALL',NOW)['best_contract']);self.assertIsNone(select(chain(),600,'CALL',NOW,target_distance=1000)['best_contract'])
        self.assertAlmostEqual(expected_move(100,.2,1),20)
    def test_tiers_and_score_cannot_override(self):
        self.assertEqual([tier(x) for x in (100,90,89,85,84,75,74,65,64,None)],['A+','A+','A','A','B','B','C','C','NO TRADE','NO TRADE'])
        s=build({}, {'regime':'UNSAFE'},{},q(),{'quality':'DATA_INCOMPLETE','risk':'UNAVAILABLE'},market_session(NOW),{'ready':False},NOW);self.assertFalse(s.actionable);self.assertTrue(s.hard_rejection);self.assertIsNone(s.score)
    def test_watchdog_only_expected_active_and_once(self):
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d)/'db.sqlite');w=Watchdog(s);session=market_session(NOW)
            self.assertFalse(w.check(session,NOW));self.assertFalse(w.check(session,NOW+timedelta(seconds=599)));self.assertTrue(w.check(session,NOW+timedelta(seconds=600)));self.assertFalse(w.check(session,NOW+timedelta(seconds=610)))
            s.put('last_market:sip',{'source_timestamp':(NOW+timedelta(seconds=611)).isoformat()});self.assertFalse(w.check(session,NOW+timedelta(seconds=611)));s.close()
    def test_paper_costs_idempotency_stale_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=PaperEngine(Path(d)/'paper.sqlite');contract=select(chain(),600,'CALL',NOW)['best_contract'];signal=Signal('fixture',NOW.isoformat(),NOW.isoformat(),'fixture',score=80,option_contract=contract,signal_expiry=(NOW+timedelta(seconds=60)).isoformat(),rejection_reasons=['STRATEGY_PROSPECTIVE_VALIDATION_MISSING'])
            a=p.open(signal,q(contract['symbol'],2,2.1),now=NOW,synthetic=True);self.assertEqual(a['entry'],'2.11');self.assertEqual(p.open(signal,q(),now=NOW),'ALREADY_RECORDED')
            after=NOW+timedelta(seconds=10);r=p.mark('fixture',q(contract['symbol'],2.5,2.6,after),'TARGET',now=after);self.assertEqual(r['pnl_usd'],'36.70');self.assertEqual(r['status'],'CLOSED')
            with self.assertRaises(ValueError):p.mark('fixture',q(),now=NOW+timedelta(seconds=20))
            p.store.close()
    def test_private_position_mark_and_invalidation(self):
        position={'contract':'SPY261009C00600000','quantity':1,'cost_usd':'210.65'}
        r=review(position,q(position['contract'],2.5,2.6),q(bid=590,ask=591),{'invalidation':595},now=NOW);self.assertIn('UNDERLYING_INVALIDATION',r['alerts']);self.assertAlmostEqual(r['estimated_pnl_usd'],39.35)
        r=review(position,q(),None,now=NOW+timedelta(minutes=1));self.assertIsNone(r['estimated_pnl_usd'])
    def test_expiration_never_assumes_sale(self):
        r=review({'contract':'SPY261002C00600000','quantity':1,'cost_usd':'200'},None,None,now=NOW);self.assertEqual(r['quantity'],1);self.assertIn('EXPIRATION_PASSED_MANUAL_RECONCILIATION_REQUIRED',r['alerts'])
    def test_news_missing_and_blackout(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'news.json';n=NewsProvider(f);self.assertEqual(n.snapshot(NOW)['risk'],'UNAVAILABLE')
            from news.calendar_updater import event,SOURCES
            e=event('CPI','CPI',NOW+timedelta(minutes=10),SOURCES['bls'].format(year=2026),NOW.isoformat())
            f.write_text(json.dumps({'verified_at':NOW.isoformat(),'source_url':SOURCES['fed'],'coverage_from':(NOW-timedelta(days=1)).isoformat(),'coverage_through':(NOW+timedelta(days=1)).isoformat(),'coverage_complete':True,'events':[e]}));self.assertEqual(n.snapshot(NOW)['risk'],'HIGH')
    def test_audit_append_only_backup_restore(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'source';root.mkdir();s=Store(root/'db.sqlite');s.put('test',{'a':1});s.audit('one','test','fixture',{});s.audit('one','test','fixture',{})
            self.assertEqual(s.db.execute('SELECT count(*) FROM audit').fetchone()[0],1)
            with self.assertRaises(sqlite3.IntegrityError):s.db.execute('DELETE FROM audit')
            s.db.rollback();backup(Path(d)/'backup',root);restore(Path(d)/'backup',Path(d)/'restored');r=Store(Path(d)/'restored/db.sqlite');self.assertEqual(r.get('test'),{'a':1});r.close();s.close()
    def test_stream_messagepack_and_old_quote(self):
        from data.stream import Stream,encode,decode
        self.assertEqual(decode(encode([{'T':'success'}],True),True),[{'T':'success'}])
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d)/'db.sqlite');stream=Stream(s);now=datetime.now(timezone.utc)
            self.assertTrue(stream.ingest({'T':'q','S':'SPY','bp':600,'ap':601,'t':now.isoformat()}));self.assertFalse(stream.ingest({'T':'q','S':'SPY','bp':1,'ap':2,'t':(now-timedelta(seconds=30)).isoformat()}));self.assertEqual(s.get('quote:SPY')['payload']['bid'],600);s.close()
if __name__=='__main__':unittest.main()
