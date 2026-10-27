import hashlib
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core.storage import Store
from core.paper_actions import execute
from data.models import quote
from monitoring.message_format import status_text, idea_text, diagnostics_text, health_text, update_text, number, score_summary_text, paper_summary_text, position_review_text
from monitoring.position_monitor import review
from monitoring.paper_alerts import emit
from monitoring.research_populations import horizon_summary, horizon_text

NOW = datetime(2026, 10, 14, 15, 0, tzinfo=timezone.utc)

def underlying(now=NOW):
    return quote('alpaca-iex', 'SPY', {'bp': 499.99, 'ap': 500.01, 't': now.isoformat()}, received=now.isoformat()).view(now)

def context():
    bars=[dict(timestamp=NOW.timestamp()-(31-n)*60,open=499.,high=501.,low=498.,close=499.7+n*.01,volume=100) for n in range(31)]
    return {'quote':underlying(),'feed_quality':'IEX','reason':None,'bar_research':{'quality':'COMPLETED_BAR_RESEARCH_ONLY','reason':None,'bars':bars,'features':{'1m':{'vwap_approx':499.5}},'feed_quality':'IEX'},'features':{'1m':{'trend':'BULL'}}}

def idea():
    return {'signal_id': 'a' * 24, 'strategy_version': 'spy-ideas-v2-observed', 'setup_type': 'TREND_CONTINUATION',
            'timestamp': NOW.isoformat(), 'signal_expiry': (NOW + timedelta(minutes=10)).isoformat(),
            'max_hold_until': (NOW + timedelta(hours=1)).isoformat(), 'horizon_id': 'H60', 'direction': 'CALL',
            'trigger_level': 499.5, 'reference_midpoint': 500, 'modeled_entry_fill': 500.02,
            'entry': 500, 'trigger': 499.5, 'spy_price': 500, 'invalidation': 499, 't1': 501, 't2': 502,
            'feed_quality': 'IEX', 'explanation': ['Completed 15m frame confirms context.']}

class SemanticMessageTests(unittest.TestCase):
    def test_status_names_separate_horizons_without_probabilities_or_option_premium(self):
        text = status_text(context(), NOW, {'quality': 'DATA_OK', 'risk': 'NORMAL'})
        for expected in ('Current trend: UP', 'Next hour: upward bias', 'Research · IEX', 'New entry: WAIT'):
            self.assertIn(expected, text)
        self.assertNotIn('win chance', text)
        self.assertLessEqual(len(text.splitlines()), 5)
        self.assertNotIn('None', text)

    def test_confirmed_underlying_candidate_is_watch_only_not_contradictory_wait_buy(self):
        text = status_text(context(), NOW, {'quality': 'DATA_OK', 'risk': 'NORMAL'}, entry_reason='BUY CALL idea (unvalidated)')
        self.assertIn('New entry: WAIT — underlying watch; option gates separate', text)
        self.assertNotIn('WAIT — BUY', text)
        self.assertNotIn('BUY CALL', text)

    def test_completed_bar_view_does_not_promote_stale_quote_or_calendar(self):
        ctx=context();ctx.update(quote=underlying(NOW-timedelta(seconds=40)),reason='data not fresh',failed_predicate='SOURCE_TOO_OLD')
        text=status_text(ctx,NOW,{'quality':'DATA_INCOMPLETE','risk':'UNAVAILABLE'})
        self.assertIn('SPY $500.00',text);self.assertIn('Last completed-bar trend: UP',text);self.assertIn('Next hour: unavailable',text)
        self.assertIn('WAIT — fresh price unavailable',text);self.assertNotIn('SOURCE_TOO_OLD',text)
        details=diagnostics_text(ctx,NOW,{'quality':'DATA_INCOMPLETE','risk':'UNAVAILABLE'})
        self.assertIn('SOURCE_TOO_OLD',details);self.assertIn('DATA_INCOMPLETE',details)

    def test_missing_horizon_remains_unavailable_and_closed_session_blocks_entries(self):
        ctx = context();ctx['horizons'] = {'H60': {'bias': 'UP'}}
        text = status_text(ctx, NOW.replace(day=17), {'quality': 'DATA_OK', 'risk': 'NORMAL'})
        self.assertIn('Current trend: UNAVAILABLE', text)
        self.assertIn('Next hour: unavailable', text)
        self.assertIn('WAIT — market closed', text)

    def test_idea_named_prices_and_watch_only_no_guessed_contract(self):
        row = idea();row['actual_reported_fill'] = 999.99
        text = idea_text(row, {'evidence_tag': 'INSUFFICIENT', 'closed': 3}, {})
        for expected in ('ID ' + 'a' * 24, '60 minutes', 'above SPY $499.50', 'Underlying watch only · option contract unavailable.', 'Experimental'):
            self.assertIn(expected, text)
        self.assertEqual(row['reference_midpoint'],500);self.assertEqual(row['modeled_entry_fill'],500.02);self.assertEqual(row['actual_reported_fill'],999.99)
        self.assertNotIn('999.99', text)
        self.assertNotIn('Pick the option yourself', text)
        self.assertNotIn('Rough risk', text)

    def test_verified_option_plan_distinguishes_premium_at_risk_from_modeled_stop(self):
        row = idea();symbol = 'SPY261016C00500000'
        oq = quote('alpaca-opra', symbol, {'bp': 1.9, 'ap': 2., 't': NOW.isoformat()}, received=NOW.isoformat()).view(NOW)
        row.update(option_contract={'symbol':symbol,'quote':oq,'type':'C','expiry':'2026-10-16','strike':500,'bid':1.9,'ask':2.,'mid':1.95,'volume':100,'oi':100,'delta':.5,'gamma':.01,'theta':-.1,'vega':.1,'iv':.2,'greeks_timestamp':NOW.isoformat()},option_plan={'limit':2.,'stop_bid':1.5},option_verification='FRESH_QUOTE_GREEKS_CHAIN_SANITY_PASSED')
        text = idea_text(row, {'closed': 0}, {})
        self.assertIn(symbol, text)
        self.assertIn('premium at risk $200.00 + fees', text)
        self.assertIn('no guaranteed stop-loss cap', text)
        row['option_contract']['quote'] = quote('alpaca-opra', symbol, {'bp': 1.9, 'ap': 2.1, 't': (NOW - timedelta(minutes=1)).isoformat()}, received=NOW.isoformat()).view(NOW)
        self.assertIn('Underlying watch only · option contract unavailable.', idea_text(row, {'closed': 0}, {}))

    def test_details_preserve_signed_ages_and_never_print_raw_objects(self):
        ctx = context();ctx['diagnostics'] = [{'provider': 'alpaca-iex', 'source_age_seconds': -.125, 'receipt_age_seconds': -.01, 'source_receipt_skew_seconds': .115, 'predicate': 'RECEIPT_FUTURE'}]
        text = diagnostics_text(ctx, NOW, {'quality': 'DATA_INCOMPLETE', 'risk': 'UNAVAILABLE'})
        self.assertIn('source age -0.125 s', text)
        self.assertIn('receipt age -0.010 s', text)
        self.assertIn('RECEIPT_FUTURE', text)
        self.assertNotIn("{'", text)
        self.assertNotIn('None', text)
        self.assertLessEqual(len(text), 3400)

    def test_health_and_monitoring_messages_have_semantic_labels(self):
        text = health_text({'system': {'worker': {'state': 'RUNNING', 'at': NOW.isoformat(), 'fresh_heartbeat': True}}, 'news': {'quality': 'DATA_INCOMPLETE'}, 'ntp_clock': {'state': 'MEASURED', 'offset_seconds': .12345}, 'skew_budget_seconds': 2}, NOW)
        self.assertIn('worker: RUNNING', text)
        self.assertIn('offset 0.123 s', text)
        self.assertNotIn("{'", text)
        self.assertIn('no exit confirmed', update_text(idea(), 'MONITORING_UNAVAILABLE'))
        for bad in (None, float('nan'), float('inf'), {}, True):self.assertEqual(number(bad), 'UNAVAILABLE')

    def test_stale_position_inputs_leave_reported_holding_open_and_unmarked(self):
        result = review({'contract': 'SPY261016C00500000', 'quantity': 1, 'cost_usd': 200}, {}, underlying(NOW - timedelta(seconds=30)), {'invalidation': 501}, now=NOW)
        self.assertEqual(result['quantity'], 1)
        self.assertEqual(result['position_status'], 'USER_REPORTED_OPEN_NOT_BROKER_VERIFIED')
        self.assertIsNone(result['estimated_pnl_usd'])
        self.assertTrue(any('MONITORING_UNAVAILABLE' in item for item in result['alerts']))
        self.assertNotIn('UNDERLYING_INVALIDATION', result['alerts'])

    def test_current_idea_more_callback_preserves_named_prices_and_guest_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / 'fixture.sqlite')
            try:
                row = idea();store.event('fixture-candidate', 'paper_candidate', row)
                text = execute({'signal_id': row['signal_id'], 'action': 'more'}, store, NOW)['text']
                self.assertIn('Confirmation trigger: 499.50', text)
                self.assertIn('Reference midpoint: 500.00', text)
                self.assertIn('Modeled entry fill: 500.02', text)
                self.assertIn('already handled', execute({'signal_id': row['signal_id'], 'action': 'more'}, store, NOW)['text'])
                with self.assertRaisesRegex(ValueError, 'OWNER_ONLY'):execute({'signal_id': row['signal_id'], 'action': 'more', 'tenant': 'b' * 24}, store, NOW)
            finally:store.close()

    def test_option_paper_update_names_exact_initial_event_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / 'fixture.sqlite');events = []
            try:
                row = idea();config = {'paper_daily_message_cap': 8, 'notifications': {'profile': 'simple', 'categories': {'idea_updates': True}}, 'signals': {'shared': True}}
                def enqueue(*args, **kwargs):events.append(kwargs)
                self.assertTrue(emit(store, row, 'PAPER_UPDATE', config, enqueue, NOW, text='EXAMPLE research update'))
                expected = 'paper-' + hashlib.sha256((row['signal_id'] + row['strategy_version'] + 'PAPER_SIGNAL').encode()).hexdigest()[:32]
                self.assertEqual(events[0]['parent_event_id'], expected)
            finally:store.close()

    def test_score_formats_baseline_metrics_without_raw_dicts_or_pooled_odds(self):
        text = score_summary_text({'windows': {'today': {'closed': 2, 'average_r': .25, 'expectancy_ci95': [-1., 1.5], 'evidence_tag': 'INSUFFICIENT DATA'}}, 'setups': {'ORB': {'closed': 2, 'evidence_tag': 'INSUFFICIENT DATA'}}, 'paired_baseline_comparison': {'closed_pairs': 2, 'mean_difference_r': .1, 'ci95': [-.2, .4]}})
        self.assertIn('95% interval -1.00 to 1.50', text)
        self.assertIn('not random entry times', text)
        self.assertIn('Setups/variants being tested: 1', text)
        self.assertNotIn("{'", text)
        self.assertNotIn('None', text)

    def test_paper_populations_and_unavailable_options_are_labeled_separately(self):
        text = paper_summary_text({'all': {'total': 8, 'closed': 4}}, [], {'proxy': {'closed': 2, 'open': 1}}, {'overall': {'n': 0}}, {'evaluations': 13261, 'outcomes': 13180})
        for expected in ('Underlying ideas = setup observations', 'Underlying proxy = separate modeled SPY shares', 'Real-quote option paper = genuine bid/ask simulation', 'Forward diagnostics = candidate evaluations, not trades', 'Option performance unavailable'):
            self.assertIn(expected, text)
        self.assertNotIn("{'", text)
        self.assertNotIn('None', text)

    def test_horizon_population_is_separate_read_only_and_does_not_create_missing_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'horizon_ideas.sqlite'
            self.assertEqual(horizon_summary(path)['status'], 'NOT_COLLECTED')
            self.assertFalse(path.exists())
            db = sqlite3.connect(path);db.execute('CREATE TABLE idea_events(payload TEXT)')
            for value in ({'signal_id': 'old', 'population': 'LEGACY', 'horizon_id': 'H60', 'status': 'CLOSED'},
                          {'signal_id': 'new', 'population': 'HORIZON_COMPARISON_UNDERLYING_ONLY', 'horizon_id': 'H60', 'status': 'OPEN', 'trial_id': 'fixture-h60'},
                          {'signal_id': 'new', 'population': 'HORIZON_COMPARISON_UNDERLYING_ONLY', 'horizon_id': 'H60', 'status': 'CLOSED', 'trial_id': 'fixture-h60'}):
                db.execute('INSERT INTO idea_events VALUES(?)', (json.dumps(value),))
            db.commit();db.close();before = path.read_bytes()
            result = horizon_summary(path)
            self.assertEqual(result['by_horizon']['H60']['tracked'], 1)
            self.assertEqual(result['by_horizon']['H60']['closed'], 1)
            self.assertEqual(result['trials'], 1)
            self.assertEqual(path.read_bytes(), before)
            text = horizon_text(result);self.assertIn('never pooled with legacy ideas or option paper', text)
            self.assertNotIn('old', text)

    def test_private_position_review_is_explicit_about_missing_monitoring_and_full_exit(self):
        text = position_review_text({'contract': 'SPY261016C00500000'}, 'MONITORING_UNAVAILABLE', {'invalidation': None, 't1': 501, 't2': 502}, underlying(NOW - timedelta(seconds=30)), {}, NOW)
        self.assertIn('PRIVATE POSITION REVIEW', text)
        self.assertIn('SPY UNAVAILABLE', text)
        self.assertIn('no exit or position closure inferred', text)
        self.assertIn('Full-exit/manual review only', text)
        self.assertNotIn('None', text)
        self.assertNotIn('sell half', text.lower())

if __name__ == '__main__':unittest.main()
