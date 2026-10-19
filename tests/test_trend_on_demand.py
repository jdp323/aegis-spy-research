import json,tempfile,unittest,urllib.error
from pathlib import Path
from datetime import timedelta
from unittest.mock import patch,Mock
from contextlib import contextmanager
import data.trend_spy as feed
from research.basic_trend import on_demand_text
import test_basic_trend as fixtures

class TrendOnDemandTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.root_patch=patch.object(feed,'ROOT',self.root);self.root_patch.start();self.addCleanup(self.root_patch.stop)
        self.raw=fixtures.BasicTrendTests().raw(volume=100)

    def seed(self,raw):feed.save(self.root/'research/basic_trend_raw.json',raw)
    def transport(self):
        response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False);response.read.return_value=b'fixture-body'
        return response
    def test_fresh_fetch_and_shared_30_second_cache(self):
        with patch.object(feed.urllib.request,'urlopen',return_value=self.transport()) as request,patch.object(feed,'parse_chart',return_value=self.raw['bars']):
            first=feed.refresh(max_age_seconds=30);second=feed.refresh(max_age_seconds=30)
        self.assertEqual(first['refresh_mode'],'FRESH_FETCH');self.assertEqual(second['refresh_mode'],'RECENT_CACHE');self.assertEqual(request.call_count,1)
        self.assertTrue((self.root/'data/premarket_cache'/(first['sha256']+'.json')).exists())
        self.assertEqual(request.call_args.kwargs['timeout'],8)
    def test_command_refreshes_31_second_cache_worker_preserves_300(self):
        now=fixtures.NOW;raw={**self.raw,'fetched_at':(now-timedelta(seconds=31)).isoformat()};self.seed(raw)
        with patch.object(feed.urllib.request,'urlopen',return_value=self.transport()) as request,patch.object(feed,'parse_chart',return_value=self.raw['bars']):
            self.assertEqual(feed.refresh(now)['refresh_mode'],'RECENT_CACHE');request.assert_not_called()
            self.assertEqual(feed.refresh(now,max_age_seconds=30)['refresh_mode'],'FRESH_FETCH');request.assert_called_once()
    def test_failure_is_reserved_and_throttled_not_old_success(self):
        self.seed({**self.raw,'fetched_at':(fixtures.NOW-timedelta(minutes=6)).isoformat()})
        with patch.object(feed.urllib.request,'urlopen',side_effect=urllib.error.HTTPError(feed.URL,429,'rate limited',None,None)) as request:
            first=feed.refresh(fixtures.NOW,max_age_seconds=30)
            second=feed.refresh(fixtures.NOW+timedelta(seconds=59),max_age_seconds=30)
        self.assertEqual(first['status'],'UNAVAILABLE');self.assertEqual(first['bars'],[]);self.assertEqual(second['refresh_mode'],'FAILURE_COOLDOWN');self.assertEqual(request.call_count,1)
    def test_reserved_killed_attempt_has_failure_cooldown(self):
        self.seed({**self.raw,'status':'FETCH_RESERVED','bars':[]})
        with patch.object(feed.urllib.request,'urlopen') as request:
            self.assertEqual(feed.refresh(fixtures.NOW,max_age_seconds=30)['refresh_mode'],'FAILURE_COOLDOWN');request.assert_not_called()
    def test_lock_contention_no_duplicate_request(self):
        self.seed(self.raw)
        with feed.refresh_lock(wait_seconds=0) as first:
            self.assertTrue(first)
            with feed.refresh_lock(wait_seconds=0) as second:self.assertFalse(second)
        with feed.refresh_lock(wait_seconds=0) as recovered:self.assertTrue(recovered)
    def test_busy_reader_labels_snapshot_without_network(self):
        self.seed(self.raw)
        @contextmanager
        def busy():yield False
        with patch.object(feed,'refresh_lock',busy),patch.object(feed.urllib.request,'urlopen') as request:
            self.assertEqual(feed.refresh(fixtures.NOW,max_age_seconds=30)['refresh_mode'],'REFRESH_IN_PROGRESS');request.assert_not_called()
    def test_corrupt_cache_and_future_timestamp_do_not_block_refresh(self):
        for old in ([],{**self.raw,'fetched_at':(fixtures.NOW+timedelta(days=1)).isoformat()}):
            self.seed(old)
            with patch.object(feed.urllib.request,'urlopen',return_value=self.transport()) as request,patch.object(feed,'parse_chart',return_value=self.raw['bars']):
                self.assertEqual(feed.refresh(fixtures.NOW,max_age_seconds=30)['refresh_mode'],'FRESH_FETCH');request.assert_called_once()
    def test_each_request_reanalyzes_cache_with_fetch_and_observation_times(self):
        with patch.object(feed,'refresh',return_value={**self.raw,'refresh_mode':'RECENT_CACHE'}) as refresh,patch('research.basic_trend.verified',return_value=True),patch('monitoring.research_alerts.load',return_value={}):
            a=on_demand_text(fixtures.NOW);b=on_demand_text(fixtures.NOW+timedelta(seconds=1))
        self.assertEqual(refresh.call_count,2);self.assertIn('SPY TREND: UP',a);self.assertIn('Observed through',a);self.assertIn('FETCHED:',a);self.assertIn('ANALYZED:',a);self.assertIn('30-second',a);self.assertNotEqual(a,b);self.assertIn('not the chance',a)
    def test_failed_fetch_never_uses_saved_report(self):
        with patch.object(feed,'refresh',return_value={'status':'UNAVAILABLE','reason':'HTTP_429','refresh_mode':'FETCH_FAILED'}),patch('monitoring.research_alerts.load') as old:
            text=on_demand_text(fixtures.NOW)
        old.assert_not_called();self.assertIn('0% usable coverage',text);self.assertIn('HTTP_429',text);self.assertNotIn('SPY TREND: UP',text)
    def test_early_open_uses_fresh_payload_three_check_fallback(self):
        now=fixtures.NOW.replace(hour=13,minute=50);raw={**self.raw,'fetched_at':now.isoformat()}
        raw['bars']=[{**b,'timestamp':int((now-timedelta(minutes=(3-i)*5)).timestamp())} for i,b in enumerate(raw['bars'][:3])]
        with patch.object(feed,'refresh',return_value={**raw,'refresh_mode':'FRESH_FETCH'}),patch('research.basic_trend.verified',return_value=True),patch('monitoring.research_alerts.load',return_value={}):
            text=on_demand_text(now)
        self.assertIn('SPY TREND: UP',text);self.assertIn('three fallback checks',text);self.assertIn('LAST OBSERVED: $602.00',text);self.assertIn('09:50 ET',text)
    def test_current_matched_source_disagreement_blocks_direction(self):
        now=fixtures.NOW.replace(hour=15,minute=0);raw={**self.raw,'fetched_at':now.isoformat()}
        for b in raw['bars']:b['timestamp']+=int((now-fixtures.NOW).total_seconds())
        prior={'source_fetched_at':now.isoformat(),'multi_source':{'intraday_comparison':{'status':'DISAGREEMENT','bar':(now-timedelta(minutes=5)).isoformat()}}}
        with patch.object(feed,'refresh',return_value={**raw,'refresh_mode':'FRESH_FETCH'}),patch('research.basic_trend.verified',return_value=True),patch('monitoring.research_alerts.load',return_value=prior):
            text=on_demand_text(now)
        self.assertIn('sources disagree',text);self.assertNotIn('SPY TREND: UP',text)
    def test_invalid_provenance_never_fallback(self):
        with patch.object(feed,'refresh',return_value={**self.raw,'refresh_mode':'FRESH_FETCH'}),patch('research.basic_trend.verified',return_value=False),patch('monitoring.research_alerts.load') as old:
            text=on_demand_text(fixtures.NOW)
        old.assert_not_called();self.assertIn('0% usable coverage',text)

if __name__=='__main__':unittest.main()
