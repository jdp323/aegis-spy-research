"""Real scheduled path: prepared evidence, fake clocks, zero network/guests."""
import unittest
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from core.idea_service import scheduled_preopen,preopen_text
from monitoring.day_schedule import dispatch
from monitoring.premarket_brief import build
from ops.day_simulation import MemoryStore,config
from tests.test_premarket_brief import fixture,NOW

class ScheduledMorning(unittest.TestCase):
    def setUp(self):
        self.store=MemoryStore();self.config=config();self.news={'quality':'DATA_OK','risk':'NORMAL','events':[]}
        self.clock=patch('core.idea_service.datetime',wraps=datetime).start();self.clock.now.return_value=NOW+timedelta(seconds=8)
        self.addCleanup(patch.stopall)
        patch('monitoring.premarket_brief.verified',return_value=True).start()
        self.collect=patch('data.premarket_spy.collect_once',side_effect=AssertionError('dispatch must not fetch')).start()
        self.outlook_build=patch('news.market_outlook.build',return_value={'bias':'MIXED','news':{'bias':'DOWN'}}).start()
        self.prepared=build(fixture(NOW+timedelta(seconds=6)),self.news,NOW+timedelta(seconds=8))
        self.store.put('premarket_prepared:2026-10-06',self.prepared)
    def test_post_fetch_clock_keeps_fresh_prepared_snapshot(self):
        message=scheduled_preopen(self.store,self.news,NOW,self.config);r=self.store.get('premarket_report:2026-10-06')
        self.assertEqual(r['quality'],'PUBLIC_RESEARCH_ONLY');self.assertEqual(r['message_version'],'spy-preopen-compact-v1')
        self.assertIn('Today’s outlook: UP',message);self.assertEqual(len(message.splitlines()),7);self.collect.assert_not_called()
        self.assertNotIn('probability',message);self.assertNotIn('4 of 4',message)
    def test_actual_dispatch_private_once_without_live_path(self):
        out=[]
        for _ in range(2):dispatch(self.store,NOW,self.config,lambda k:scheduled_preopen(self.store,self.news,NOW,self.config),out.append)
        self.assertEqual(len(out),1);self.assertEqual(out[0]['audience'],'PRIVATE');self.assertEqual(out[0]['kind'],'RESEARCH');self.assertEqual(out[0]['alert_type'],'PREOPEN');self.collect.assert_not_called()
        self.assertNotIn('BUY',out[0]['text']);self.assertNotIn('SELL',out[0]['text'])
    def test_crossing_window_never_reserves_or_sends_late(self):
        self.clock.now.return_value=NOW+timedelta(minutes=5);out=[]
        dispatch(self.store,NOW,self.config,lambda k:scheduled_preopen(self.store,self.news,NOW,self.config),out.append)
        self.assertFalse(out);self.assertIsNone(self.store.get('v5-slot:PREOPEN:2026-10-06'))
    def test_outside_window_disabled_holiday_never_fetch(self):
        for n in (NOW-timedelta(seconds=1),NOW+timedelta(minutes=5),datetime(2026,10,10,13,15,tzinfo=timezone.utc),datetime(2026,11,26,14,15,tzinfo=timezone.utc)):
            self.assertIsNone(scheduled_preopen(self.store,self.news,n,self.config))
        self.config['notifications']['categories']['morning']=False;self.assertIsNone(scheduled_preopen(self.store,self.news,NOW,self.config));self.collect.assert_not_called()
    def test_preparation_failure_honest_abstention_no_fabricated_levels(self):
        self.store.data.clear();m=scheduled_preopen(self.store,self.news,NOW,self.config)
        self.assertIn('DATA UNAVAILABLE',m);self.assertNotIn('$',m);self.assertIn('reassess after the open',m)
    def test_future_prepared_snapshot_rejected(self):
        self.store.put('premarket_prepared:2026-10-06',dict(self.prepared,generated_at=(NOW+timedelta(seconds=30)).isoformat()))
        scheduled_preopen(self.store,self.news,NOW,self.config);self.assertEqual(self.store.get('premarket_report:2026-10-06')['quality'],'UNAVAILABLE')
    def test_old_preparation_not_promoted_by_price_only_fallback(self):
        self.store.put('premarket_prepared:2026-10-06',dict(self.prepared,generated_at=(NOW-timedelta(minutes=11)).isoformat()))
        self.store.put('market_outlook',{'bias':'UP','market':{'price':999,'bias':'UP'}})
        m=scheduled_preopen(self.store,self.news,NOW,self.config);self.assertIn('DATA UNAVAILABLE',m);self.assertNotIn('999',m)
    def test_missing_checks_are_sideways_not_forced_by_news(self):
        r={'quality':'PUBLIC_RESEARCH_ONLY','bias':'MIXED / WAIT','levels':{'last':500}}
        self.store.put('market_outlook',{'bias':'UP'});m=preopen_text(self.store,self.news,NOW,self.config,r)
        self.assertIn('outlook: SIDEWAYS',m);self.assertNotIn('of 4',m);self.assertIn('unavailable',m)
    def test_simulation_fake_clock_no_fetch_no_real_context(self):
        self.store.put('premarket_report:2026-10-06',{'quality':'SIMULATED','bias':'UP','levels':{'last':500}})
        self.clock.now.return_value=NOW+timedelta(days=1);m=scheduled_preopen(self.store,self.news,NOW,self.config,simulation=True)
        self.assertIn('Oct 06',m);self.collect.assert_not_called();self.outlook_build.assert_not_called()
    def test_dst_early_close_schedule(self):
        winter=datetime(2026,11,27,14,15,tzinfo=timezone.utc);self.clock.now.return_value=winter+timedelta(seconds=1)
        m=scheduled_preopen(self.store,self.news,winter,self.config);self.assertIn('Nov 27',m);self.assertEqual(len(m.splitlines()),7);self.assertIsNotNone(self.store.get('premarket_report:2026-11-27'))

if __name__=='__main__':unittest.main()
