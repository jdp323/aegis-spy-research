import tempfile,unittest
from pathlib import Path
from datetime import timedelta
from core.storage import Store
from core.sessions import market_session
from tests.test_research_alerts import fixture,NOW
from monitoring.research_alerts import update,observe,changes,context,change_text,settings

class ResearchHighlightTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.path=Path(self.folder.name)/'fixture.sqlite';self.store=Store(self.path);self.addCleanup(lambda:self.store.close());self.events=[]
    def publish(self,store,id,text,**kwargs):self.events.append({'id':id,'text':text,'kind':kwargs['kind']})
    def send(self,now,raw):return update(self.store,raw,market_session(now),{},self.publish,now)
    def down(self,now):
        raw=fixture(now);raw['levels'].update(last_close=597,low=596,bar_based_vwap_approx=600)
        raw['patterns'].update(structure_3bars='LOWER_HIGHS_LOWER_LOWS',vwap_relationship='BELOW',patterns=['CLOSE_BELOW_OPENING_RANGE']);return raw
    def test_change_alert_names_structure_vwap_range_and_movement(self):
        self.send(NOW,fixture());later=NOW+timedelta(minutes=10);self.assertTrue(self.send(later,self.down(later)))
        text=self.events[-1]['text']
        for phrase in ('SPY OUTLOOK','turned downward','lost approximate','below the first15','moved -','BIAS: DOWN','no option trade instruction','Delay UNVERIFIED'.lower()):
            self.assertIn(phrase,text if phrase!='delay unverified' else text.lower())
        for phrase in ('BUY PUT','BUY CALL','SELL NOW','PRIVATE_SECRET'):self.assertNotIn(phrase,text)
        self.assertLess(len(text),3500);self.assertEqual(self.events[-1]['kind'],'RESEARCH')
    def test_reclaim_and_upward_recovery(self):
        old=context(observe(self.down(NOW),market_session(NOW),NOW));later=NOW+timedelta(minutes=10);o=observe(fixture(later),market_session(later),later)
        highlights=changes(o,old,market_session(later));self.assertTrue(any('reclaimed' in x for x in highlights));self.assertIn('Call-side research lens only',change_text(o,highlights,later))
    def test_material_move_without_structure_change(self):
        self.send(NOW,fixture());later=NOW+timedelta(minutes=10);raw=fixture(later);raw['levels'].update(last_close=605,high=606)
        self.assertTrue(self.send(later,raw));self.assertIn('moved +',self.events[-1]['text']);self.assertNotIn('turned upward',self.events[-1]['text'])
    def test_cooldown_pending_change_then_restart_dedupe(self):
        self.send(NOW,fixture());later=NOW+timedelta(minutes=5);self.assertIsNone(self.send(later,self.down(later)))
        self.store.close();self.store=Store(self.path);later=NOW+timedelta(minutes=10);self.assertTrue(self.send(later,self.down(later)))
        self.assertIsNone(self.send(later,self.down(later)));later+=timedelta(minutes=10);self.assertIsNone(self.send(later,self.down(later)));self.assertEqual(len(self.events),2)
    def test_same_bar_old_session_or_gap_not_used_as_transition(self):
        o=observe(fixture(),market_session(NOW),NOW);old=context(o)
        self.assertEqual(changes(o,old,market_session(NOW)),[])
        old['session_date']='2026-10-02';self.assertEqual(changes(o,old,market_session(NOW)),[])
        old=context(o);old['bar']=(o['bar']-timedelta(hours=1)).isoformat();self.assertEqual(changes(o,old,market_session(NOW)),[])
    def test_no_stale_or_closed_session_highlights(self):
        old=context(observe(fixture(),market_session(NOW),NOW));later=NOW+timedelta(hours=1)
        o=observe(fixture(),market_session(later),later);self.assertEqual(changes(o,old,market_session(later)),[])
        later=NOW.replace(hour=21);self.assertEqual(changes(observe(fixture(later),market_session(later),later),old,market_session(later)),[])
    def test_range_labels_independently_match_price(self):
        raw=fixture();raw['patterns']['patterns']=['CLOSE_BELOW_OPENING_RANGE']
        self.assertEqual(observe(raw,market_session(NOW),NOW)['reason'],'OPENING_RANGE_MISMATCH')
    def test_failed_publication_does_not_advance_comparison_baseline(self):
        self.send(NOW,fixture());old=self.store.get('automatic_research');later=NOW+timedelta(minutes=10)
        def fail(*args,**kwargs):raise OSError('disk')
        with self.assertRaises(OSError):update(self.store,self.down(later),market_session(later),{},fail,later)
        self.assertEqual(self.store.get('automatic_research'),old)
    def test_movement_threshold_configuration(self):
        for bad in (True,0,.05,6,float('nan'),'0.3'):
            with self.assertRaises(ValueError):settings({'research_notifications':{'move_alert_pct':bad}})

if __name__=='__main__':unittest.main()
