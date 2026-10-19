"""Offline clock/transport tests for the actual V5 scheduled morning path."""
import unittest
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from core.idea_service import scheduled_preopen,preopen_text
from monitoring.day_schedule import dispatch
from ops.day_simulation import MemoryStore,config
from tests.test_premarket_brief import fixture,NOW

class ScheduledMorning(unittest.TestCase):
    def setUp(self):
        self.store=MemoryStore();self.config=config()
        self.news={'quality':'DATA_OK','risk':'NORMAL','verified_at':NOW.isoformat(),'events':[]}
        self.outlook={'bias':'MIXED','news':{'bias':'DOWN','support':{'counts':{'UP':0,'DOWN':2,'NEUTRAL':1},'total':3},'items':[]}}
        self.clock=patch('core.idea_service.datetime',wraps=datetime).start()
        self.clock.now.return_value=NOW+timedelta(seconds=8)
        self.addCleanup(patch.stopall)
        patch('monitoring.premarket_brief.verified',return_value=True).start()
        self.collect=patch('data.premarket_spy.collect_once',return_value=fixture(NOW+timedelta(seconds=6))).start()
        self.outlook_build=patch('news.market_outlook.build',return_value=self.outlook).start()

    def test_post_fetch_clock_keeps_fresh_snapshot_and_recomputes_context(self):
        message=scheduled_preopen(self.store,self.news,NOW,self.config)
        report=self.store.get('premarket_report:2026-10-06')
        self.assertEqual(report['quality'],'PUBLIC_RESEARCH_ONLY')
        self.assertEqual(report['generated_at'],(NOW+timedelta(seconds=8)).isoformat())
        self.assertEqual(report['message_version'],'spy-preopen-v4-observed')
        self.assertIn('OUTLOOK: MIXED | price evidence: UP',message)
        self.assertIn('4 of 4 UP',message)
        self.assertIn('News context: DOWN',message)
        self.assertIn('2 of 3 DOWN',message)
        self.assertIn('NOT ESTABLISHED',message)
        self.assertIn('not odds',message)
        self.assertIn('public premarket bars are not live',message)
        self.assertLess(len(message),3500)
        self.assertEqual(self.outlook_build.call_args.kwargs['premarket']['quality'],'PUBLIC_RESEARCH_ONLY')

    def test_actual_dispatch_private_once_without_live_path(self):
        delivered=[]
        compose=lambda kind:scheduled_preopen(self.store,self.news,NOW,self.config)
        dispatch(self.store,NOW,self.config,compose,delivered.append)
        dispatch(self.store,NOW,self.config,compose,delivered.append)
        self.assertEqual(len(delivered),1)
        self.assertEqual(delivered[0]['kind'],'RESEARCH')
        self.assertEqual(delivered[0]['audience'],'PRIVATE')
        self.assertEqual(delivered[0]['tenant'],'owner')
        self.assertEqual(delivered[0]['alert_type'],'PREOPEN')
        self.assertNotIn('BUY',delivered[0]['text'])
        self.assertNotIn('SELL',delivered[0]['text'])
        self.assertEqual(self.collect.call_count,1)

    def test_fetch_crossing_window_never_reserves_or_sends_late(self):
        self.clock.now.return_value=NOW+timedelta(minutes=5)
        delivered=[]
        dispatch(self.store,NOW,self.config,lambda k:scheduled_preopen(self.store,self.news,NOW,self.config),delivered.append)
        self.assertEqual(delivered,[])
        self.assertIsNone(self.store.get('v5-slot:PREOPEN:2026-10-06'))
        self.assertIsNone(self.store.get('premarket_report:2026-10-06'))

    def test_outside_window_disabled_holiday_never_fetch(self):
        for now in (NOW-timedelta(seconds=1),NOW+timedelta(minutes=5),datetime(2026,10,10,13,15,tzinfo=timezone.utc),datetime(2026,11,26,14,15,tzinfo=timezone.utc)):
            self.assertIsNone(scheduled_preopen(self.store,self.news,now,self.config))
        self.config['notifications']['categories']['morning']=False
        self.assertIsNone(scheduled_preopen(self.store,self.news,NOW,self.config))
        self.collect.assert_not_called()

    def test_collection_failure_still_has_honest_news_only_report(self):
        self.collect.side_effect=OSError('fixture unavailable')
        message=scheduled_preopen(self.store,self.news,NOW,self.config)
        self.assertIn('price evidence: UNAVAILABLE',message)
        self.assertIn('no usable directional sample',message)
        self.assertIn('News context: DOWN',message)
        self.assertIn('Option contract/premium: UNAVAILABLE',message)

    def test_future_snapshot_remains_rejected(self):
        self.collect.return_value=fixture(NOW+timedelta(seconds=30))
        scheduled_preopen(self.store,self.news,NOW,self.config)
        self.assertEqual(self.store.get('premarket_report:2026-10-06')['quality'],'UNAVAILABLE')

    def test_price_only_fallback_is_identified_without_volume_levels(self):
        self.outlook.update(bias='UP',market={'bias':'UP','mode':'PUBLIC FIVE-MINUTE BARS; DELAY UNVERIFIED','as_of':(NOW-timedelta(minutes=5)).isoformat(),'price':500.25,'counts':{'UP':4,'DOWN':0,'NEUTRAL':0}})
        self.collect.return_value={}
        message=scheduled_preopen(self.store,self.news,NOW,self.config)
        self.assertIn('OUTLOOK: UP | price evidence: UP',message)
        self.assertIn('Fallback price checks: 4 of 4 UP',message)
        self.assertIn('PUBLIC FIVE-MINUTE BARS; DELAY UNVERIFIED',message)
        self.assertIn('observed through 09:10 ET',message)
        self.assertIn('not an executable quote',message)
        self.assertIn('no volume-confirmed premarket setup',message)
        self.assertNotIn('Holds above UNAVAILABLE',message)
        self.assertNotIn('VWAP, gap',message)

    def test_missing_checks_excluded_and_news_never_uses_combined_bias(self):
        self.store.put('market_outlook',{'bias':'UP','news':{'bias':'DOWN','support':self.outlook['news']['support']}})
        r={'quality':'PUBLIC_RESEARCH_ONLY','bias':'MIXED / WAIT','levels':{'last':500.,'vwap_approx':500.},'timeframes':{'15m':{'trend':'UNAVAILABLE'},'30m':{'trend':'FLAT'}}}
        message=preopen_text(self.store,self.news,NOW,self.config,r)
        self.assertIn('2 of 2 NEUTRAL',message)
        self.assertNotIn('of 4',message)
        self.assertIn('News context: DOWN',message)

    def test_simulation_uses_fake_clock_no_fetch_no_real_context(self):
        self.store.put('premarket_report:2026-10-06',{'quality':'SIMULATED','bias':'UP'})
        self.clock.now.return_value=NOW+timedelta(days=1)
        message=scheduled_preopen(self.store,self.news,NOW,self.config,simulation=True)
        self.assertIn('09:15 ET',message)
        self.collect.assert_not_called();self.outlook_build.assert_not_called()

    def test_dst_early_close_schedule(self):
        winter=datetime(2026,11,27,14,15,tzinfo=timezone.utc)
        self.clock.now.return_value=winter+timedelta(seconds=1)
        self.collect.return_value={}
        message=scheduled_preopen(self.store,self.news,winter,self.config)
        self.assertIn('09:15 ET',message)
        self.assertIsNotNone(self.store.get('premarket_report:2026-11-27'))

if __name__=='__main__':unittest.main()
