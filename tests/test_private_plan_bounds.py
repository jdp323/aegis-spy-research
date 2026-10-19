import copy
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from core.bot_commands import execute
from monitoring.position_rules import review_deadline
from monitoring.message_format import measured
from options.ledger import Ledger

NOW = datetime(2026, 10, 14, 15, 0, tzinfo=timezone.utc)

class MemoryStore:
    def __init__(self, data=None):self.data = data or {};self.audits = []
    def get(self, key, default=None):return self.data.get(key, default)
    def put(self, key, value):self.data[key] = copy.deepcopy(value)
    def audit(self, *args):self.audits.append(args)
    def close(self):pass

def clock_at(value):
    class Frozen(datetime):
        @classmethod
        def now(cls, tz=None):return value.astimezone(tz) if tz else value.replace(tzinfo=None)
    return Frozen

class PrivatePlanBounds(unittest.TestCase):
    def test_regular_session_plan_is_capped_and_short_plan_keeps_requested_deadline(self):
        long = review_deadline(NOW, '2026-10-16', 1440)
        self.assertTrue(long['allowed']);self.assertTrue(long['shortened'])
        self.assertEqual(long['deadline'], '2026-10-14T19:55:00+00:00')
        short = review_deadline(NOW, '2026-10-16', 60)
        self.assertEqual(short['deadline'], '2026-10-14T16:00:00+00:00');self.assertFalse(short['shortened'])

    def test_early_close_and_dst_week_use_verified_et_cutoff(self):
        early = review_deadline(datetime(2026, 11, 27, 17, 30, tzinfo=timezone.utc), '2026-12-04', 120)
        self.assertEqual(early['deadline'], '2026-11-27T17:55:00+00:00')
        dst = review_deadline(datetime(2026, 11, 2, 16, 0, tzinfo=timezone.utc), '2026-11-06', 1440)
        self.assertEqual(dst['deadline'], '2026-11-02T20:55:00+00:00')

    def test_unknown_calendar_closed_session_and_cutoff_refuse_new_plan_precisely(self):
        cases = [(datetime(2028, 10, 16, 15, tzinfo=timezone.utc), '2028-12-29', 'exchange calendar unavailable'),
                 (datetime(2026, 10, 17, 15, tzinfo=timezone.utc), '2026-10-23', 'session is CLOSED'),
                 (datetime(2026, 10, 14, 19, 55, tzinfo=timezone.utc), '2026-10-16', 'cutoff 15:55 ET')]
        for now, expiry, reason in cases:
            with self.subTest(reason=reason):
                rule = review_deadline(now, expiry, 60)
                self.assertFalse(rule['allowed']);self.assertIn(reason, rule['reason'])
        with self.assertRaisesRegex(ValueError, 'AWARE_TIME_REQUIRED'):review_deadline(NOW.replace(tzinfo=None), '2026-10-16', 60)

    def test_expiry_refusal_does_not_infer_exercise_or_settlement(self):
        rule = review_deadline(datetime(2026, 10, 19, 15, tzinfo=timezone.utc), '2026-10-16', 60)
        self.assertFalse(rule['allowed']);self.assertIn('expiry has passed', rule['reason'])
        self.assertIn('No settlement, exercise or closure is inferred', rule['reason'])

    def test_plan_command_stores_bounded_deadline_and_retains_reported_fill(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Ledger(Path(tmp) / 'reported.sqlite')
            try:
                symbol = 'SPY261016C00500000';ledger.record('fixture-fill', 'BUY', symbol, 1, '2', '.65', '2026-10-14T10:00:00-04:00')
                before = ledger.db.execute('SELECT count(*) FROM option_events').fetchone()[0];store = MemoryStore()
                with patch('core.bot_commands.Store', return_value=store), patch('core.bot_commands.books', side_effect=lambda:{'owner':ledger.positions()}), patch('core.bot_commands.datetime', clock_at(NOW)):
                    text = execute({'command':'plan','text':symbol+' 499 501 502 1440','id':'fixture-plan'})
                plan = store.data['plan:owner:'+symbol]
                self.assertEqual(plan['max_hold_until'], '2026-10-14T19:55:00+00:00')
                self.assertEqual(plan['requested_hold_minutes'], 1440);self.assertEqual(plan['holding_policy_version'], 'private-intraday-review-v2')
                self.assertIn('requested horizon shortened', text);self.assertEqual(len(store.audits), 1)
                self.assertEqual(ledger.db.execute('SELECT count(*) FROM option_events').fetchone()[0], before)
                self.assertEqual(ledger.positions()[0]['quantity'], 1)
            finally:ledger.close()

    def test_refused_plan_leaves_existing_plan_and_fill_untouched(self):
        for now, symbol, reason in [(datetime(2026, 10, 17, 15, tzinfo=timezone.utc),'SPY261023C00500000','session is CLOSED'),
                                    (datetime(2026, 10, 19, 15, tzinfo=timezone.utc),'SPY261016C00500000','expiry has passed')]:
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as tmp:
                ledger = Ledger(Path(tmp) / 'reported.sqlite')
                try:
                    ledger.record('fixture-fill', 'BUY', symbol, 1, '2', '.65', '2026-10-14T10:00:00-04:00')
                    key='plan:owner:'+symbol;previous={'invalidation':498,'max_hold_until':'2026-10-14T19:55:00+00:00'};store=MemoryStore({key:copy.deepcopy(previous)})
                    with patch('core.bot_commands.Store', return_value=store), patch('core.bot_commands.books', side_effect=lambda:{'owner':ledger.positions()}), patch('core.bot_commands.datetime', clock_at(now)):
                        text=execute({'command':'plan','text':symbol+' 499 501 502 60','id':'fixture-refused'})
                    self.assertIn(reason,text);self.assertIn('reported fill and holding are retained',text)
                    self.assertEqual(store.data[key],previous);self.assertEqual(store.audits,[])
                    self.assertEqual(ledger.db.execute('SELECT count(*) FROM option_events').fetchone()[0],1);self.assertEqual(ledger.positions()[0]['quantity'],1)
                finally:ledger.close()

    def test_nested_measures_are_semantic_and_missing_remains_unavailable(self):
        value={'frames':{'15m':'BULL','1h':None},'known_opposing':0,'unavailable':['1h'],'matched':False}
        text=measured(value,300)
        self.assertIn('15m=BULL',text);self.assertIn('1h=UNAVAILABLE',text);self.assertIn('matched=no',text)
        self.assertNotIn("{'",text);self.assertNotIn('None',text);self.assertNotIn('[\'',text)
        self.assertEqual(measured(None),'UNAVAILABLE');self.assertEqual(measured(float('nan')),'UNAVAILABLE')

    def test_why_command_uses_semantic_measured_values(self):
        trace={'at':NOW.isoformat(),'engine_version':'fixture-trace-v1','setup':'TREND_CONTINUATION','direction':'CALL','blocker':None,
               'checks':{'higher_frame':{'state':'PASS','value':{'frames':{'15m':'BULL','1h':None},'known_opposing':0},'threshold':'known opposing < 2'},
                         'volume_ratio':{'state':'NOT_EVALUATED','value':None,'threshold':1.2}}}
        store=MemoryStore({'v6-latest-setup-traces':[trace]})
        class Tracker:
            def __init__(self,*args):pass
            def close(self):pass
        ctx={'reason':None,'features':{},'opening_range_status':'AVAILABLE'}
        with patch('core.bot_commands.Store',return_value=store), patch('core.upgrade_service.read_config',return_value={'idea_engine_enabled':True}), patch('core.idea_service.context',return_value=ctx), patch('core.idea_service.candidates',return_value=([],None)), patch('news.engine.NewsProvider.snapshot',return_value={'quality':'DATA_OK','risk':'NORMAL'}), patch('backtesting.idea_tracker.IdeaTracker',Tracker):
            text=execute({'command':'why','id':'fixture-why'})
        self.assertIn('15m=BULL',text);self.assertIn('1h=UNAVAILABLE',text)
        self.assertIn('volume_ratio NOT_EVALUATED [value UNAVAILABLE',text)
        self.assertNotIn("{'",text);self.assertNotIn('None',text)

if __name__=='__main__':unittest.main()
