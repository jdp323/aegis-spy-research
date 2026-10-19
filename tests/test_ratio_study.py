import unittest,tempfile
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from core.storage import Store
import tests.test_basic_trend as basic_fixtures
NOW=basic_fixtures.NOW
from research.basic_trend import analyze,text_for
from research.ratio_study import tick,summary
class RatioStudyTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup);self.store=Store(Path(self.folder.name)/'db.sqlite');self.addCleanup(self.store.close)
    def raw(self,direction=1):return basic_fixtures.BasicTrendTests().raw(direction)
    def run_tick(self,raw,now=NOW):
        with patch('research.ratio_study.verified',return_value=True),patch('research.basic_trend.verified',return_value=True):tick(self.store,raw,now)
    def outcome(self,item,fall=False):
        raw=self.raw();now=datetime.fromtimestamp(item['target_bar']+300,timezone.utc);raw['fetched_at']=now.isoformat()
        last=raw['bars'][-1]['timestamp']
        for ts in range(last+300,item['target_bar']+1,300):
            p=600-(ts-last)/300 if fall else 600+(ts-last)/300
            raw['bars'].append({'timestamp':ts,'open':p,'high':p+1,'low':p-1,'close':p,'volume':0})
        return raw,now
    def test_percentages_are_check_shares_and_sum_to_100(self):
        for direction,label in ((1,'UP'),(-1,'DOWN'),(0,'NEUTRAL')):
            with patch('research.basic_trend.verified',return_value=True):r=analyze(self.raw(direction),NOW)
            s=r['support'];self.assertEqual(sum(s[k] for k in ('up_pct','down_pct','neutral_pct')),100);self.assertEqual(s['counts'][label],4);self.assertIn('not the chance',text_for(r))
    def test_no_data_uses_coverage_not_fake_up_down_odds(self):
        text=text_for(analyze({},NOW));self.assertIn('0% usable coverage',text);self.assertNotIn('UP 50%',text)
    def test_pending_and_idempotent_issue_future_baseline(self):
        self.run_tick(self.raw());self.run_tick(self.raw());s=summary(self.store);self.assertEqual(s['observations'],1);self.assertEqual(s['pending'],1);self.assertIsNone(s['active_hit_pct']);self.assertIsNone(s['calibrated_probability'])
        item=self.store.events('ratio_study')[0];self.assertGreater(item['baseline_bar'],NOW.timestamp());self.assertEqual(item['target_bar']-item['baseline_bar'],900)
    def test_future_outcome_correct_and_incorrect(self):
        for fall in (False,True):
            with self.subTest(fall=fall):
                with tempfile.TemporaryDirectory() as folder:
                    store=Store(Path(folder)/'db.sqlite')
                    with patch('research.ratio_study.verified',return_value=True),patch('research.basic_trend.verified',return_value=True):
                        tick(store,self.raw(),NOW);item=store.events('ratio_study')[0];raw,now=self.outcome(item,fall);tick(store,raw,now)
                    s=summary(store);self.assertEqual(s['resolved'],1);self.assertEqual(s['active_hit_pct'],0 if fall else 100);self.assertFalse(s['automatic_promotion']);store.close()
    def test_missing_future_path_is_not_interpolated(self):
        self.run_tick(self.raw());item=self.store.events('ratio_study')[0];raw,now=self.outcome(item);raw['bars']=[b for b in raw['bars'] if b['timestamp']!=item['baseline_bar']+300];self.run_tick(raw,now);self.assertIsNone(self.store.get('ratio_result:'+item['id']))
    def test_revised_settled_prices_excluded_without_erasing_original(self):
        self.run_tick(self.raw());item=self.store.events('ratio_study')[0];raw,now=self.outcome(item);self.run_tick(raw,now);old=self.store.get('ratio_result:'+item['id']);raw['bars'][-1]['close']+=.1;self.run_tick(raw,now);self.assertEqual(self.store.get('ratio_result:'+item['id']),old);self.assertEqual(summary(self.store)['revision_rejections'],1);self.assertEqual(summary(self.store)['resolved'],0)
    def test_no_overlapping_samples_or_stale_input(self):
        self.run_tick(self.raw());self.run_tick(self.raw(),NOW+timedelta(minutes=5));self.assertEqual(summary(self.store)['observations'],1)
        self.run_tick(self.raw(),NOW+timedelta(hours=1));self.assertEqual(summary(self.store)['observations'],1)
    def test_no_outcome_crosses_market_open(self):
        raw=self.raw();now=NOW.replace(hour=13,minute=20);offset=int((now-NOW).total_seconds())
        raw['fetched_at']=now.isoformat()
        for b in raw['bars']:b['timestamp']+=offset
        self.run_tick(raw,now);self.assertEqual(summary(self.store)['observations'],0)
    def test_small_sample_has_no_improvement_promotion(self):
        self.run_tick(self.raw());item=self.store.events('ratio_study')[0];raw,now=self.outcome(item);self.run_tick(raw,now);s=summary(self.store);self.assertEqual(s['improvement_state'],'COLLECTING_EVIDENCE');self.assertFalse(s['automatic_promotion'])
    def test_three_check_fallback_discloses_denominator(self):
        from tests.test_research_alerts import fixture,NOW as regular_now
        from monitoring.research_alerts import observe,short_text
        from core.sessions import market_session
        with patch('data.trend_spy.load',return_value={}):text=short_text(observe(fixture(),market_session(regular_now),regular_now),market_session(regular_now),regular_now)
        self.assertIn('three fallback checks',text);self.assertIn('UP 100.0%',text)
if __name__=='__main__':unittest.main()
