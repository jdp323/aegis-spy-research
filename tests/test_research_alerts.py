import copy
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch
from core.sessions import market_session
from core.storage import Store
from monitoring.research_alerts import observe,update,text_for,settings,SOURCE

NOW=datetime(2026,10,5,17,0,tzinfo=timezone.utc)
def fixture(now=NOW):
    bar=now.replace(minute=(now.minute//5)*5,second=0,microsecond=0)-timedelta(minutes=5)
    return {'generated_at':now.isoformat(),'source_fetched_at':now.isoformat(),'source':SOURCE,
        'data_use':'DELAYED_OR_UNVERIFIED_RESEARCH_ONLY','data_status':'RESEARCH_DATA_RECEIVED',
        'levels':{'session_date':bar.date().isoformat(),'last_completed_bar_at':bar.isoformat(),'last_close':603,'high':604,'low':598,'open':599,'bar_based_vwap_approx':601},
        'patterns':{'status':'DESCRIPTIVE_ONLY','session':bar.date().isoformat(),'as_of_bar':int(bar.timestamp()),'structure_3bars':'HIGHER_HIGHS_HIGHER_LOWS','vwap_relationship':'ABOVE','patterns':['CLOSE_ABOVE_OPENING_RANGE'],'opening_range_15m':{'low':598,'high':600}}}

class ResearchAlerts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=Store(Path(self.temp.name)/'db.sqlite');self.events=[]
    def tearDown(self):self.store.close();self.temp.cleanup()
    def publish(self,*args,**kwargs):self.events.append((args,kwargs))
    def send(self,now=NOW,doc=None):return update(self.store,doc or fixture(now),market_session(now),{},self.publish,now)
    def test_public_only_and_allowlisted_shared_fields(self):
        d=fixture();d['positions']={'owner_balance':'PRIVATE_SECRET'}
        o=observe(d,market_session(NOW),NOW);self.assertEqual(o['quality'],'PUBLIC_RESEARCH_ONLY')
        text=text_for(o,market_session(NOW),NOW)
        for expected in ('TREND: BULLISH','12:55-13:00 ET','ACTION: NO TRADE','Delay UNVERIFIED','USD'):self.assertIn(expected,text)
        for prohibited in ('PRIVATE_SECRET','BUY CALL','BUY PUT','SELL NOW'):self.assertNotIn(prohibited,text)
        self.assertLess(len(text),3500)
    def test_restart_dedupe_and_periodic_brief(self):
        a=self.send();self.assertTrue(a);self.assertIsNone(self.send())
        self.store.close();self.store=Store(Path(self.temp.name)/'db.sqlite')
        self.assertIsNone(self.send(NOW+timedelta(minutes=29)))
        self.assertTrue(self.send(NOW+timedelta(minutes=30)))
        self.assertEqual(len(self.events),2);self.assertEqual(self.events[0][1]['kind'],'RESEARCH')
    def test_meaningful_change_cooldown(self):
        self.send();later=NOW+timedelta(minutes=5);d=fixture(later);d['patterns']['structure_3bars']='MIXED'
        self.assertIsNone(self.send(later,d))
        later=NOW+timedelta(minutes=10);d=fixture(later);d['patterns']['structure_3bars']='MIXED'
        self.assertTrue(self.send(later,d))
    def test_stale_or_bad_public_inputs_never_supply_price(self):
        for mutate in (
            lambda d:d.update(source='https://untrusted.test'),
            lambda d:d.update(source_fetched_at=(NOW-timedelta(hours=1)).isoformat()),
            lambda d:d.update(generated_at=(NOW+timedelta(minutes=1)).isoformat()),
            lambda d:d['levels'].update(last_close=float('nan')),
            lambda d:d['levels'].update(last_close=605),
            lambda d:d['patterns'].update(as_of_bar=1),
            lambda d:d['patterns'].update(vwap_relationship='BELOW'),
            lambda d:d['levels'].update(last_completed_bar_at=NOW.isoformat()),
            lambda d:d.update(levels=None),
        ):
            with self.subTest(mutate=mutate):
                d=fixture();mutate(d);o=observe(d,market_session(NOW),NOW)
                self.assertEqual(o['quality'],'UNAVAILABLE');self.assertNotIn('$',text_for(o,market_session(NOW),NOW))
        old=NOW-timedelta(minutes=30);d=fixture(old);d.update(generated_at=NOW.isoformat(),source_fetched_at=NOW.isoformat())
        self.assertEqual(observe(d,market_session(NOW),NOW)['reason'],'PUBLIC_BAR_STALE')
    def test_outage_once_then_recovery(self):
        doc={'broken':True}
        self.assertTrue(self.send(doc=doc));self.assertIsNone(self.send(NOW+timedelta(hours=1),doc))
        self.assertTrue(self.send(NOW+timedelta(hours=1)))
    def test_no_state_commit_on_failed_publication(self):
        def fail(*args,**kw):raise OSError('disk unavailable')
        with self.assertRaises(OSError):update(self.store,fixture(),market_session(NOW),{},fail,NOW)
        self.assertIsNone(self.store.get('automatic_research'));self.assertTrue(self.send())
    def test_offhours_weekend_and_night_cadence(self):
        fri=datetime(2026,10,2,20,tzinfo=timezone.utc);doc=fixture(fri)
        sat=datetime(2026,10,3,16,tzinfo=timezone.utc);doc.update(generated_at=sat.isoformat(),source_fetched_at=sat.isoformat())
        self.assertTrue(self.send(sat,doc))
        later=sat+timedelta(hours=5);doc.update(generated_at=later.isoformat(),source_fetched_at=later.isoformat())
        self.assertIsNone(self.send(later,doc))
        later=sat+timedelta(hours=6);doc.update(generated_at=later.isoformat(),source_fetched_at=later.isoformat())
        self.assertTrue(self.send(later,doc))
        self.assertIsNone(self.send(sat.replace(hour=6),doc))
    def test_holiday_early_close_and_calendar_fail_closed(self):
        for bar in (datetime(2026,11,26,17,tzinfo=timezone.utc),datetime(2026,11,27,19,tzinfo=timezone.utc)):
            now=bar+timedelta(minutes=5);d=fixture(now)
            self.assertEqual(observe(d,market_session(now),now)['quality'],'UNAVAILABLE')
        nextyear=NOW.replace(year=2028)
        self.assertEqual(observe(fixture(nextyear),market_session(nextyear),nextyear)['reason'],'CALENDAR_UNAVAILABLE')
    def test_disabled_and_bad_configuration(self):
        self.assertIsNone(update(self.store,fixture(),market_session(NOW),{'research_notifications':{'enabled':False}},self.publish,NOW))
        for value in (1,False,'300'):
            with self.assertRaises(ValueError):settings({'research_notifications':{'regular_seconds':value}})
    def test_worker_wires_notifications_without_entitled_provider(self):
        from core.upgrade_service import Engine
        from data.providers import AlpacaProvider
        with patch.dict('os.environ',{},clear=True),patch('news.market_outlook.RSSProvider.fetch',return_value=b'<rss><channel/></rss>'),patch('core.upgrade_service.books',return_value={}),patch('core.upgrade_service.PaperEngine') as paper,patch('monitoring.research_alerts.load',return_value=fixture()),patch('monitoring.research_alerts.update') as called:
            paper.return_value.positions.return_value=[]
            paper.return_value.risk_state.return_value={'daily_loss_usd':0,'consecutive_losses':0,'daily_reconciled_date':datetime.now(timezone.utc).astimezone(__import__('core.sessions',fromlist=['ET']).ET).date().isoformat(),'positions':[]}
            from core.storage import ROOT
            local=Path(self.temp.name);(local/'config').mkdir(exist_ok=True);(local/'monitoring').mkdir(exist_ok=True);(local/'config/upgrade.json').write_bytes((ROOT/'config/upgrade.json').read_bytes())
            with patch('core.upgrade_service.ROOT',local):
                engine=Engine(self.store,AlpacaProvider())
                try:engine.tick();called.assert_not_called() # simple profile is intentionally quiet
                finally:engine.close()
    def test_atomic_outbox_duplicate_keeps_original_payload(self):
        from core.upgrade_service import enqueue
        root=Path(self.temp.name);(root/'monitoring').mkdir()
        with patch('core.upgrade_service.ROOT',root):
            enqueue(self.store,'fixture-brief','First',kind='RESEARCH')
            target=root/'monitoring/outbox/fixture-brief.json';original=target.read_bytes()
            enqueue(self.store,'fixture-brief','Changed',kind='RESEARCH')
            self.assertEqual(target.read_bytes(),original)
            import json
            self.assertEqual(json.loads(original)['audience'],'SHARED')
            self.assertFalse(list(target.parent.glob('*.pending')))

if __name__=='__main__':unittest.main()
