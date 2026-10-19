import tempfile,unittest,copy
from pathlib import Path
from datetime import timedelta
from unittest.mock import patch
from core.storage import Store
from core.sessions import market_session
from research.forward_study import tick,summary
from tests.test_research_alerts import NOW,fixture

def raw(doc):
    anchor=int(__import__('datetime').datetime.fromisoformat(doc['levels']['last_completed_bar_at']).timestamp())
    return {'source':doc['source'],'symbol':'SPY','status':'RESEARCH_DATA_RECEIVED','fetched_at':doc['source_fetched_at'],'sha256':'a'*64,'bars':[{'timestamp':anchor,'open':602,'high':604,'low':601,'close':603,'volume':100}]}

class ForwardStudyTests(unittest.TestCase):
 def setUp(self):
    self.temp=tempfile.TemporaryDirectory();self.s=Store(Path(self.temp.name)/'study.sqlite');self.cache=patch('research.forward_study.verified_cache',return_value=True);self.cache.start()
 def tearDown(self):self.cache.stop();self.s.close();self.temp.cleanup()
 def test_prospective_once_no_backfilled_outcomes(self):
    doc=fixture();r=raw(doc);tick(self.s,doc,r,market_session(NOW),NOW);tick(self.s,doc,r,market_session(NOW),NOW)
    self.assertEqual(summary(self.s)['observations'],1);self.assertEqual(summary(self.s)['pending'],1)
    self.assertIsNone(summary(self.s)['directional_accuracy'])
    item=self.s.events('forward_study')[0];self.assertEqual(item['direction'],'UP');self.assertGreater(item['target_bar_start'],NOW.timestamp());self.assertEqual(item['action'],'NO TRADE')
 def test_public_chart_partial_non_aligned_tail_is_ignored(self):
    d=fixture();r=raw(d);r['bars'].append({'timestamp':int(NOW.timestamp())-23,'open':603,'high':604,'low':602,'close':603,'volume':100})
    tick(self.s,d,r,market_session(NOW),NOW);self.assertEqual(summary(self.s)['observations'],1)
 def test_future_path_exact_target_gap_and_revision(self):
    doc=fixture();r=raw(doc);tick(self.s,doc,r,market_session(NOW),NOW);item=self.s.events('forward_study')[0]
    later=NOW+timedelta(minutes=40);d=fixture(later);d['patterns']['structure_3bars']='MIXED'
    r.update(fetched_at=d['source_fetched_at']);r['bars']=[{'timestamp':ts,'open':602,'high':605,'low':601,'close':603 if ts!=item['target_bar_start'] else 604,'volume':100} for ts in range(item['anchor_bar_start'],int(later.timestamp()),300)]
    gap=copy.deepcopy(r);gap['bars'].pop(2);tick(self.s,d,gap,market_session(later),later)
    self.assertEqual(summary(self.s)['resolved'],0)
    tick(self.s,d,r,market_session(later),later)
    result=self.s.get('forward_result:'+item['id']);self.assertTrue(result['direction_correct']);self.assertAlmostEqual(result['underlying_return_bps'],(604/603-1)*10000)
    self.assertNotIn('pnl',result);self.assertEqual(summary(self.s)['abstentions'],1)
 def test_revised_anchor_rejected(self):
    doc=fixture();r=raw(doc);tick(self.s,doc,r,market_session(NOW),NOW);item=self.s.events('forward_study')[0]
    later=NOW+timedelta(minutes=40);d=fixture(later);r.update(fetched_at=d['source_fetched_at']);r['bars']=[{'timestamp':ts,'open':602,'high':605,'low':601,'close':603,'volume':100} for ts in range(item['anchor_bar_start'],int(later.timestamp()),300)];r['bars'][0]['close']=602.5
    tick(self.s,d,r,market_session(later),later);self.assertEqual(summary(self.s)['revision_rejections'],1)
 def test_stale_source_bad_cache_or_wrong_symbol_no_forecast(self):
    d=fixture();r=raw(d)
    with patch('research.forward_study.verified_cache',return_value=False):tick(self.s,d,r,market_session(NOW),NOW)
    self.assertEqual(summary(self.s)['observations'],0)
    r['symbol']='QQQ';tick(self.s,d,r,market_session(NOW),NOW);self.assertEqual(summary(self.s)['observations'],0)
    tick(self.s,d,raw(d),market_session(NOW+timedelta(hours=1)),NOW+timedelta(hours=1));self.assertEqual(summary(self.s)['observations'],0)
 def test_does_not_open_near_close_or_outside_session(self):
    late=NOW.replace(hour=19,minute=45);doc=fixture(late);tick(self.s,doc,raw(doc),market_session(late),late)
    self.assertEqual(summary(self.s)['observations'],0)
 def test_cooldown_issued_clock_and_abstain(self):
    d=fixture();d['patterns']['structure_3bars']='MIXED';tick(self.s,d,raw(d),market_session(NOW),NOW)
    later=NOW+timedelta(minutes=5);d=fixture(later);tick(self.s,d,raw(d),market_session(later),later)
    self.assertEqual(summary(self.s)['observations'],1);self.assertEqual(summary(self.s)['abstentions'],1)
 def test_new_observation_does_not_overlap_prior_outcome_path(self):
    d=fixture();tick(self.s,d,raw(d),market_session(NOW),NOW)
    later=NOW+timedelta(minutes=30);d=fixture(later);tick(self.s,d,raw(d),market_session(later),later)
    self.assertEqual(summary(self.s)['observations'],1)

if __name__=='__main__':unittest.main()
