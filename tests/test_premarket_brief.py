import json,hashlib,io,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from core.storage import Store
from monitoring import premarket_brief as pre
from data import premarket_spy as data
NOW=datetime(2026,10,6,13,15,tzinfo=timezone.utc)
def fixture(now=NOW):
    prior=datetime(2026,10,5,13,30,tzinfo=timezone.utc);start=datetime(2026,10,6,8,tzinfo=timezone.utc)
    def bar(t,p):return {'timestamp':int(t.timestamp()),'open':p,'high':p+.2,'low':p-.2,'close':p+.1,'volume':100}
    rows=[bar(prior+timedelta(minutes=5*i),600) for i in range(78)]+[bar(start+timedelta(minutes=5*i),601+i*.03) for i in range(63)]
    return {'source':data.URL,'symbol':'SPY','use':'DELAY_UNVERIFIED_RESEARCH_ONLY','session_date':'2026-10-06','status':'RESEARCH_DATA_RECEIVED','fetched_at':now.isoformat(),'bars':rows,'sha256':'a'*64}
class PremarketTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.store=Store(Path(self.folder.name)/'fixture.sqlite');self.addCleanup(self.store.close)
        self.verified=patch('monitoring.premarket_brief.verified',return_value=True);self.verified.start();self.addCleanup(self.verified.stop)
    def test_bullish_multiframe_lens_not_options_recommendation(self):
        r=pre.build(fixture(),now=NOW);self.assertEqual(r['bias'],'BULLISH');self.assertEqual(r['action'],'NO TRADE');self.assertFalse(r['validated_prediction'])
        text=pre.text_for(r);self.assertIn('Call-side research only',text);self.assertIn('15m TREND: UP',text);self.assertIn('30m TREND: UP',text);self.assertIn('NEWS / MACRO RISK: UNAVAILABLE',text);self.assertLess(len(text),3500)
    def test_bearish_lens(self):
        raw=fixture()
        for i,b in enumerate(raw['bars'][78:]):
            p=599-i*.03;b.update(open=p,high=p+.2,low=p-.2,close=p-.1)
        r=pre.build(raw,now=NOW);self.assertEqual(r['bias'],'BEARISH');self.assertIn('Put-side research only',pre.text_for(r))
    def test_missing_prior_session_and_warmup_mean_mixed(self):
        raw=fixture();raw['bars']=raw['bars'][78+40:];r=pre.build(raw,now=NOW)
        self.assertEqual(r['bias'],'MIXED / WAIT');self.assertIsNone(r['levels']['gap_pct']);self.assertEqual(r['timeframes']['30m']['trend'],'UNAVAILABLE')
    def test_stale_missing_and_cache_failure_suppress_prices(self):
        raw=fixture(NOW-timedelta(hours=1));self.assertEqual(pre.build(raw,now=NOW)['quality'],'UNAVAILABLE')
        self.assertNotIn('$',pre.text_for(pre.build({},now=NOW)))
        with patch('monitoring.premarket_brief.verified',return_value=False):self.assertEqual(pre.build(fixture(),now=NOW)['quality'],'UNAVAILABLE')
    def test_future_and_partial_bars_never_change_report(self):
        raw=fixture();original=pre.build(raw,now=NOW)
        raw['bars'].append({'timestamp':int(NOW.timestamp()),'open':9999,'high':9999,'low':9999,'close':9999,'volume':100})
        self.assertEqual(pre.build(raw,now=NOW),original)
    def test_gaps_do_not_create_complete_timeframes(self):
        raw=fixture();raw['bars']=[r for i,r in enumerate(raw['bars']) if i<78 or (i-78)%3!=1]
        r=pre.build(raw,now=NOW);self.assertEqual(r['bias'],'MIXED / WAIT');self.assertEqual(r['timeframes']['15m']['bars'],0)
    def test_indicator_warmup_resets_after_aggregate_gap(self):
        raw=fixture();raw['bars'].pop(78+45)
        r=pre.build(raw,now=NOW);self.assertIsNone(r['timeframes']['15m']['ema9']);self.assertEqual(r['bias'],'MIXED / WAIT')
    def test_schedule_exact_et_once_after_restart(self):
        emitted=[];collector=lambda day,now:fixture(now)
        def publish(store,id,text,**kw):emitted.append((id,text,kw))
        self.assertIsNone(pre.update(self.store,{}, {},publish,NOW-timedelta(seconds=1),collector))
        id=pre.update(self.store,{}, {},publish,NOW,collector);self.assertEqual(id,'premarket-mega-2026-10-06-v1')
        self.assertIsNone(pre.update(self.store,{}, {},publish,NOW+timedelta(minutes=1),collector));self.assertEqual(len(emitted),1);self.assertEqual(emitted[0][2]['kind'],'RESEARCH')
    def test_weekend_holiday_unknown_calendar_disabled_and_missed_window(self):
        collector=lambda *args:self.fail('Must not fetch')
        for date in (datetime(2026,10,10,13,15,tzinfo=timezone.utc),datetime(2026,12,25,14,15,tzinfo=timezone.utc),datetime(2028,1,4,14,15,tzinfo=timezone.utc),NOW+timedelta(minutes=5)):
            self.assertIsNone(pre.update(self.store,{}, {},lambda *a:None,date,collector))
        self.assertIsNone(pre.update(self.store,{}, {'premarket_report':{'enabled':False}},lambda *a:None,NOW,collector))
    def test_dst_and_early_close_keep_0915_et(self):
        called=[]
        def collector(day,now):called.append(day);return {}
        winter=datetime(2026,11,27,14,15,tzinfo=timezone.utc)
        self.assertIsNotNone(pre.update(self.store,{}, {},lambda *a,**k:None,winter,collector));self.assertEqual(called,['2026-11-27'])
    def test_failed_publish_not_marked_queued_and_same_id_retry(self):
        def failed(*a,**kw):raise OSError('disk unavailable')
        with self.assertRaises(OSError):pre.update(self.store,{}, {},failed,NOW,lambda *a:fixture())
        self.assertFalse(self.store.get('premarket_report:2026-10-06').get('queued',False))
        ids=[];pre.update(self.store,{}, {},lambda s,id,t,**k:ids.append(id),NOW,lambda *a:fixture());self.assertEqual(ids,['premarket-mega-2026-10-06-v1'])
    def test_news_is_optional_and_allowlisted(self):
        news={'quality':'DATA_OK','verified_at':NOW.isoformat(),'risk':'HIGH','events':[{'kind':'CPI','time':(NOW+timedelta(minutes=15)).isoformat(),'headline':'never share arbitrary fields'}]}
        text=pre.text_for(pre.build(fixture(),news,NOW));self.assertIn('CONFIGURED EVENT: CPI',text);self.assertNotIn('arbitrary',text)
    def test_invalid_config_and_saved_command_without_network(self):
        with self.assertRaises(ValueError):pre.settings({'premarket_report':{'lead_minutes':30}})
        self.assertIn('No report saved',pre.saved_text(self.store,NOW));self.assertIn('09:15 ET',pre.saved_text(self.store,NOW))
class CollectionTests(unittest.TestCase):
    def test_failed_collection_attempt_is_not_retried(self):
        with tempfile.TemporaryDirectory() as d,patch.object(data,'ROOT',Path(d)),patch('data.premarket_spy.urllib.request.urlopen',side_effect=TimeoutError) as get:
            self.assertEqual(data.collect_once('2026-10-06',NOW)['status'],'UNAVAILABLE');data.collect_once('2026-10-06',NOW);self.assertEqual(get.call_count,1)
    def test_cache_hash_and_rows_verified(self):
        body=json.dumps({'chart':{'result':[{'meta':{'symbol':'SPY'},'timestamp':[1000,1300],'indicators':{'quote':[{'open':[1,1],'high':[2,2],'low':[1,1],'close':[1,1],'volume':[10,10]}]}}]}}).encode()
        with tempfile.TemporaryDirectory() as d,patch.object(data,'ROOT',Path(d)),patch('data.premarket_spy.urllib.request.urlopen',return_value=io.BytesIO(body)):
            raw=data.collect_once('2026-10-06',NOW);self.assertTrue(data.verified(raw));raw['bars'][0]['close']=2;self.assertFalse(data.verified(raw))

if __name__=='__main__':unittest.main()
