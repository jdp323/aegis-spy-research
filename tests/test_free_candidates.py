"""Isolated synthetic rule regressions; no real strategy evidence or transport."""
import copy
import json
import unittest
from datetime import datetime, timedelta, timezone

from core.sessions import ET
from strategies.free_candidates import evaluate_shadow, RULES, RULE_HASH


def fixture(kind='ORB', direction='CALL', day='2026-10-21'):
    opening = datetime.fromisoformat(day).replace(hour=9, minute=30, tzinfo=ET)
    closes = [500 + i * .005 for i in range(25)]
    # Keep the preceding five-minute close strictly inside the opening boundary.
    # Decimal equality here would create a binary floating-point false crossing.
    closes[15:20] = [500.072,500.074,500.076,500.078,500.080]
    closes[20:] = [500.16, 500.24, 500.32, 500.40, 500.50]
    if kind == 'PULLBACK':
        closes = [500 + i * .05 for i in range(75)]
        closes[65:70] = [503.1, 502.85, 502.6, 502.35, 502.1]
        closes[70:] = [503.4, 503.55, 503.7, 503.85, 504.0]
    rows=[]
    for i, close in enumerate(closes):
        op = closes[i-1] if i else close
        rows.append({'timestamp':(opening + timedelta(minutes=i)).timestamp(),
            'open':op,'close':close,'high':max(op,close)+.025,
            'low':min(op,close)-.025,'volume':250 if i >= len(closes)-5 else 100,
            'provider':'alpaca-iex','feed_quality':'IEX'})
    if direction == 'PUT':
        for r in rows:
            r['open'],r['close'],r['high'],r['low'] = 1000-r['open'],1000-r['close'],1000-r['low'],1000-r['high']
    now = (opening + timedelta(minutes=len(closes))).astimezone(timezone.utc)
    return rows, now


def evaluate(rows,now,**kwargs):
    return evaluate_shadow(rows,now,feed='IEX',provider='alpaca-iex',**kwargs)


class FreeCandidateTests(unittest.TestCase):
    def test_frozen_two_candidate_rules_and_no_live_promotion(self):
        self.assertEqual(RULES['candidate_families'],['ORB_5M','PULLBACK_5M_15M'])
        self.assertEqual(len(RULE_HASH),64)
        self.assertFalse(RULES['broadcast']);self.assertFalse(RULES['live_ready'])

    def test_mirrored_orb_confirmation_and_full_h60(self):
        for direction in ('CALL','PUT'):
            with self.subTest(direction=direction):
                rows,now=fixture(direction=direction);result=evaluate(rows,now)
                ideas=result['candidates'];self.assertEqual(len(ideas),1,result)
                idea=ideas[0];self.assertEqual(idea['setup_type'],'ORB_5M')
                self.assertEqual(idea['direction'],direction)
                self.assertEqual(idea['confirmation_timeframe'],'5m')
                self.assertEqual(datetime.fromisoformat(idea['max_hold_until'])-now,timedelta(minutes=60))
                self.assertEqual(datetime.fromisoformat(idea['signal_expiry'])-now,timedelta(seconds=60))
                sign=1 if direction=='CALL' else -1
                self.assertGreater((idea['reference_price']-idea['invalidation'])*sign,0)
                self.assertAlmostEqual((idea['t2']-idea['reference_price'])*sign,2*idea['risk_distance'])
                self.assertFalse(idea['entry_eligible']);self.assertFalse(idea['broadcast'])
                self.assertIsNone(idea['modeled_fill']);self.assertIsNone(idea['actual_fill'])

    def test_mirrored_pullback_five_fifteen(self):
        for direction in ('CALL','PUT'):
            rows,now=fixture('PULLBACK',direction);result=evaluate(rows,now)
            self.assertEqual([x['setup_type'] for x in result['candidates']],['PULLBACK_5M_15M'],result)
            self.assertEqual(result['candidates'][0]['direction'],direction)

    def test_missing_opening_minute_never_invents_range(self):
        rows,now=fixture();del rows[7]
        self.assertEqual(evaluate(rows,now)['reason'],'GENUINE_SESSION_PREFIX_GAP')

    def test_missing_current_prefix_minute_is_not_continuity_price(self):
        rows,now=fixture();del rows[18]
        self.assertEqual(evaluate(rows,now)['reason'],'GENUINE_SESSION_PREFIX_GAP')
        rows,now=fixture();rows[18]['continuity_only']=True
        self.assertEqual(evaluate(rows,now)['reason'],'NON_GENUINE_INPUT')

    def test_unfinished_last_candle_cannot_confirm(self):
        rows,now=fixture();result=evaluate(rows,now-timedelta(seconds=1))
        self.assertFalse(result['candidates'])

    def test_old_trigger_and_entry_expiry_refused(self):
        rows,now=fixture()
        self.assertEqual(evaluate(rows,now+timedelta(seconds=60))['reason'],'NEW_ENTRY_EXPIRED')
        self.assertEqual(evaluate(rows,now+timedelta(seconds=61))['reason'],'NO_NEW_COMPLETED_5M_CONFIRMATION')
        self.assertEqual(evaluate(rows,now+timedelta(seconds=121))['reason'],'COMPLETED_BAR_AGE')

    def test_new_minute_does_not_reissue_previous_five_minute_trigger(self):
        rows,now=fixture();last=copy.deepcopy(rows[-1]);last['timestamp']+=60;rows.append(last)
        self.assertEqual(evaluate(rows,now+timedelta(minutes=1))['reason'],'WAIT_FOR_NEXT_5M_CONFIRMATION')

    def test_later_backfill_never_available_at_earlier_decision(self):
        rows,now=fixture();rows[8]['recorded_at']=(now+timedelta(minutes=5)).isoformat()
        self.assertEqual(evaluate(rows,now)['reason'],'GENUINE_SESSION_PREFIX_GAP')
        result=evaluate(rows,now,availability_mode='RETROSPECTIVE_CLOSE_ONLY')
        self.assertTrue(result['candidates']);self.assertFalse(result['candidates'][0]['strict_underlying_data_eligible'])

    def test_quote_failure_keeps_underlying_candidate_separate(self):
        rows,now=fixture()
        bad={'source_timestamp':(now-timedelta(seconds=6)).isoformat()}
        result=evaluate(rows,now,quote=bad,entry_gate={'reason':'stale','failed_predicate':'SOURCE_TOO_OLD','evaluated_at':now.isoformat()})
        self.assertTrue(result['candidates'])
        self.assertEqual(result['candidates'][0]['strict_data_reason'],'SOURCE_TOO_OLD')
        self.assertFalse(result['candidates'][0]['entry_eligible'])

    def test_identity_and_levels_unchanged_on_repeated_same_trigger(self):
        rows,now=fixture();a=evaluate(rows,now)['candidates'][0];b=evaluate(rows,now+timedelta(seconds=1))['candidates'][0]
        for key in ('signal_id','trigger','reference_price','invalidation','t1','t2','do_not_chase','signal_expiry','max_hold_until'):
            self.assertEqual(a[key],b[key],key)

    def test_stale_clock_jumps_wrong_feed_and_missing_volume(self):
        rows,now=fixture();self.assertFalse(evaluate(rows,now-timedelta(minutes=30))['candidates'])
        for key,value in [('feed_quality','SIMULATED'),('provider','yahoo-public'),('volume',None)]:
            altered=copy.deepcopy(rows);altered[0][key]=value
            self.assertFalse(evaluate(altered,now)['candidates'])
        self.assertFalse(evaluate_shadow(rows,now,feed='IEX',provider='alpaca-sip')['candidates'])

    def test_early_close_full_h60_and_dst(self):
        for day in ('2026-10-21','2026-11-02','2026-11-27'):
            rows,now=fixture(day=day);idea=evaluate(rows,now)['candidates'][0]
            self.assertEqual(now.astimezone(ET).strftime('%H:%M'),'09:55')
            self.assertEqual(datetime.fromisoformat(idea['max_hold_until']).astimezone(ET).strftime('%H:%M'),'10:55')
        rows,now=fixture(day='2026-11-27')
        # A shifted window does not fabricate an opening prefix or a late H60.
        late=now+timedelta(hours=2)
        self.assertFalse(evaluate(rows,late)['candidates'])

    def test_simulation_marked_and_option_outcomes_not_measured(self):
        rows,now=fixture();result=evaluate(rows,now,simulation=True)
        self.assertFalse(result['live_ready']);self.assertFalse(result['option_eligible'])
        self.assertEqual(result['candidates'][0]['option_performance'],'NOT_MEASURED')
        self.assertEqual(result['candidates'][0]['strict_data_reason'],'SHADOW_OR_RETROSPECTIVE_ONLY')


if __name__=='__main__':unittest.main()
