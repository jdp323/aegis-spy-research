"""Synthetic boundary tests through real constructors; no network or production state."""
import unittest,copy,json,tempfile,sqlite3,sys,time
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from core.sessions import ET
from core.market_view import build,details
from core.directional_research import view
from core.entry_publication import envelope,check
from core.primary_plan import state,current,administrative_close
from core.readonly_state import ReadOnlyState
from core.storage import Store
from data.models import quote
from ops.day_simulation import MemoryStore
from test_owner_experience import ctx,NOW
from test_complete_telegram_messages import idea
from research.shadow_forecast import prepare,future_starts,validate_result,ShadowLog,SEEDS,earlier_session_baseline
from ops.shadow_worker import bounded,environment,MINIMUM_FREE_BYTES

NEWS={'quality':'DATA_OK','risk':'NORMAL'}
def fresh_context():
    c=ctx();c.update(reason=None,quote=quote('alpaca-iex','SPY',{'bp':500.29,'ap':500.31,'t':NOW.isoformat()},received=NOW.isoformat()).view(NOW))
    return c
def plan():
    p=idea();p.update(timestamp=NOW.isoformat(),signal_expiry=(NOW+timedelta(seconds=50)).isoformat(),confirmation_at=NOW.isoformat(),confirmation_bar_start=(NOW-timedelta(minutes=1)).isoformat(),max_hold_until=(NOW+timedelta(minutes=60)).isoformat(),do_not_chase=500.8,entry_mode='ENTER NOW',status='OPEN',alerted=True)
    return p
def rows5():
    opening=NOW.astimezone(ET).replace(hour=9,minute=30);previous=opening-timedelta(days=1)
    rows=[{'symbol':'SPY','feed_quality':'IEX','origin':'STREAM','start_at':(previous+timedelta(minutes=n*5)).isoformat(),'received_at':(previous+timedelta(minutes=n*5+5)).isoformat(),'open':500.,'high':501.,'low':499.,'close':500.,'volume':100.} for n in range(78)]
    # Current context terminates at 11:00, using prior actual sessions for lookback.
    rows+= [{**rows[0],'start_at':(opening+timedelta(minutes=n*5)).isoformat(),'received_at':(opening+timedelta(minutes=n*5+5)).isoformat()} for n in range(18)]
    return rows[-78:]
def result(request):
    return {'request_id':request['id'],'paths':[{'seed':seed,'bars':[{'start_at':t,'open':500.,'high':501.,'low':499.,'close':500.+n/100,'volume':100.,'amount':50000.} for n,t in enumerate(request['future_starts'])]} for seed in SEEDS]}

class MasterBoundaries(unittest.TestCase):
    def test_shared_view_has_all_separate_answers_and_false_flags(self):
        s=build(fresh_context(),NEWS,NOW);self.assertEqual(s['trend']['state'],'UP');self.assertEqual(s['outlooks']['H60']['bias'],'UP');self.assertEqual(s['entry']['state'],'WAIT');self.assertFalse(s['entry']['option_eligible']);self.assertFalse(s['live_signal_ready']);self.assertIn('market-view-v1',details(s));self.assertEqual(s,build(fresh_context(),NEWS,NOW));self.assertIn('premarket',s);self.assertIn('recap',s)
    def test_stale_quote_preserves_only_bar_trend_abstains_forecasts(self):
        s=build(ctx(),NEWS,NOW);self.assertEqual(s['trend']['state'],'UP');self.assertTrue(s['trend']['descriptive_only']);self.assertTrue(all(o['bias']=='ABSTAIN' for o in s['outlooks'].values()));self.assertFalse(s['entry']['underlying_eligible']);self.assertEqual(s['price']['kind'],'COMPLETED_BAR_CLOSE')
    def test_quote_aging_after_context_has_a_data_reason_without_opening_gates(self):
        c=fresh_context();before=copy.deepcopy(c);aged=NOW+timedelta(seconds=6)
        s=build(c,NEWS,aged,entry_reason='setup confirmed')
        self.assertIsNone(c['reason']);self.assertEqual(c,before)
        self.assertEqual(s['entry']['reason'],'fresh price unavailable')
        self.assertEqual(s['entry']['state'],'WAIT');self.assertFalse(s['entry']['underlying_eligible']);self.assertFalse(s['entry']['option_eligible'])
        self.assertTrue(all(o['bias']=='ABSTAIN' and o['target_at'] is None for o in s['outlooks'].values()))
        self.assertEqual(s['trend']['state'],'UP');self.assertTrue(s['trend']['descriptive_only'])
    def test_aged_quote_reason_reaches_actual_status_with_active_plan(self):
        from monitoring.owner_messages import status_text
        c=fresh_context();p=plan();text=status_text(c,NOW+timedelta(seconds=6),NEWS,entry_reason='setup confirmed',plan=p)
        self.assertIn('New entry: WAIT — fresh price unavailable',text)
        self.assertIn(p['signal_id'],text);self.assertIn('monitoring unavailable',text)
        self.assertNotIn('confirmation missing',text);self.assertNotIn('I bought',text);self.assertLessEqual(len(text.splitlines()),7)
    def test_mixed_sideways_and_unavailable_are_three_distinct_states(self):
        c=fresh_context();c['bar_research']['features']['1m']['vwap_approx']=501
        self.assertEqual(view(c,NOW)['trend'],'MIXED');self.assertEqual(view(ctx(True),NOW)['trend'],'SIDEWAYS');self.assertEqual(build({},NEWS,NOW)['trend']['state'],'UNAVAILABLE')
    def test_passing_quote_does_not_override_heartbeat_calendar_or_bars(self):
        c=fresh_context();c['reason']='heartbeat old';s=build(c,NEWS,NOW);self.assertFalse(s['entry']['underlying_eligible'])
        self.assertFalse(build(fresh_context(),{},NOW)['entry']['calendar_eligible'])
    def test_bound_plan_revalidated_with_current_quote_not_saved_price(self):
        p=plan();g=envelope(p);self.assertIsNone(check(g,fresh_context(),NEWS,NOW,p))
        c=fresh_context();c['quote']['payload']['mid']=501;self.assertEqual(check(g,c,NEWS,NOW,p),'NO_CHASE_LIMIT_EXCEEDED')
        for key in ('trigger','invalidation','max_hold_until','reference_midpoint','modeled_entry_fill'):
            other=copy.deepcopy(p);other[key]='changed';self.assertEqual(check(g,fresh_context(),NEWS,NOW,other),'REGISTERED_PROPOSAL_MISMATCH')
    def test_expiry_confirmation_age_holding_cutoff_and_option_refusal(self):
        p=plan();c=fresh_context()
        at=NOW+timedelta(seconds=50);c['quote']=quote('alpaca-iex','SPY',{'bp':500.29,'ap':500.31,'t':at.isoformat()},received=at.isoformat()).view(at)
        self.assertEqual(check(envelope(p),c,NEWS,at,p),'ENTRY_WINDOW_EXPIRED_OR_INVALID')
        p['signal_expiry']=(NOW+timedelta(minutes=5)).isoformat();c['quote']=quote('alpaca-iex','SPY',{'bp':500.29,'ap':500.31,'t':(NOW+timedelta(seconds=61)).isoformat()},received=(NOW+timedelta(seconds=61)).isoformat()).view(NOW+timedelta(seconds=61))
        self.assertEqual(check(envelope(p),c,NEWS,NOW+timedelta(seconds=61),p),'CONFIRMATION_TOO_OLD')
        p=plan();p['max_hold_until']=(NOW+timedelta(minutes=59)).isoformat();self.assertEqual(check(envelope(p),fresh_context(),NEWS,NOW,p),'FULL_H60_REQUIRED')
        p=plan();p['option_contract']={'symbol':'SPY'};self.assertEqual(check(envelope(p),fresh_context(),NEWS,NOW,p),'OPTION_REFERENCE_NO_LONGER_VERIFIED')
    def test_unresolved_does_not_become_exit_at_clock_deadline(self):
        p=plan();s=MemoryStore();self.assertEqual(state(p,NOW+timedelta(hours=2)),'UNRESOLVED');before=copy.deepcopy(p)
        r=administrative_close(s,[p],p['signal_id'],'coverage cannot establish an exit',NOW+timedelta(hours=2));self.assertFalse(r['observed_exit']);self.assertIsNone(r['pnl']);self.assertEqual(p,before);self.assertIsNone(current(s,[p],NOW+timedelta(hours=2)));self.assertEqual(len(s.events('primary_admin_closure')),1)
    def test_admin_cannot_cancel_current_monitored_hold(self):
        p=plan()
        with self.assertRaisesRegex(ValueError,'ONLY_UNRESOLVED'):administrative_close(MemoryStore(),[p],p['signal_id'],'fixture',NOW)
    def test_read_only_facade_leaves_schema_and_state_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'s.sqlite';s=Store(p);s.put('x',1);s.close();r=ReadOnlyState(p);r.put('x',2);self.assertEqual(r.snapshot(['x']),{'x':1})
            with self.assertRaises(sqlite3.OperationalError):r.db.execute('UPDATE state SET payload=?',('2',))
            r.close()
    def test_full_h60_not_clipped_into_late_session(self):
        from strategies.idea_setups import detect
        from ops.day_simulation import config,inputs
        from core.idea_service import context
        s=MemoryStore();late=NOW.astimezone(ET).replace(hour=15,minute=0);inputs(s,late);c=context(s,late,True);self.assertEqual(detect(c['features'],c['bars'],c['quote'],late,config()),[])
    def test_model_horizons_early_close_dst_and_unknown_year(self):
        for at in (datetime(2026,10,27,11,tzinfo=ET),datetime(2026,11,2,11,tzinfo=ET)):
            self.assertEqual(len(future_starts(at,at,'H60')),12);self.assertEqual(len(future_starts(at,at,'H120')),24)
        at=datetime(2026,11,27,12,tzinfo=ET);self.assertEqual(len(future_starts(at,at,'SESSION')),12)
        for h in ('H120',):
            with self.assertRaisesRegex(ValueError,'FULL_HORIZON'):future_starts(at,at,h)
        with self.assertRaises(ValueError):future_starts(datetime(2030,1,2,11,tzinfo=ET),datetime(2030,1,2,11,tzinfo=ET),'H60')
    def test_model_transform_raw_individual_paths_and_no_market_mutation(self):
        raw=rows5();before=copy.deepcopy(raw);request=prepare(raw,'IEX',NOW);self.assertEqual(raw,before);self.assertEqual(request['sample_count_per_call'],1);self.assertEqual(request['input_rows'][-1]['amount'],50000.);r=validate_result(request,result(request),NOW+timedelta(seconds=1));self.assertEqual(len(r['paths']),3);self.assertTrue(r['model_generated']);self.assertFalse(r['entry_eligible'])
    def test_model_rejects_partial_missing_nonfinite_mixed_and_reversed_input(self):
        for mutate in (lambda r:r[-1].update(start_at=NOW.isoformat()),lambda r:r[-1].update(volume=None),lambda r:r[-1].update(feed_quality='SIP'),lambda r:r.reverse()):
            rows=rows5();mutate(rows)
            with self.assertRaises(ValueError):prepare(rows,'IEX',NOW)
    def test_model_invalid_raw_outputs_and_late_availability_retained_as_refusals(self):
        q=prepare(rows5(),'IEX',NOW)
        for field,value in [('high',1.),('close',float('nan'))]:
            r=result(q);r['paths'][0]['bars'][0][field]=value
            with self.assertRaises(ValueError):validate_result(q,r,NOW+timedelta(seconds=1))
        with self.assertRaisesRegex(ValueError,'TOO_LATE'):validate_result(q,result(q),NOW+timedelta(minutes=5))
        from ops.kronos_infer import safe_raw
        invalid=result(q);invalid['paths'][0]['bars'][0]['close']=float('nan');safe=safe_raw(invalid)
        self.assertEqual(safe['paths'][0]['bars'][0]['close'],'MODEL_NONFINITE_NAN')
        with self.assertRaisesRegex(ValueError,'NONFINITE'):validate_result(q,safe,NOW+timedelta(seconds=1))
    def test_model_append_only_results_and_revisions(self):
        with tempfile.TemporaryDirectory() as d:
            log=ShadowLog(Path(d)/'shadow.sqlite');self.assertTrue(log.append('one','RESULT',{'x':1},NOW));self.assertFalse(log.append('one','RESULT',{'x':2},NOW))
            with self.assertRaises(sqlite3.IntegrityError):log.db.execute('DELETE FROM shadow')
            log.close()
    def test_model_prices_and_features_cannot_enter_genuine_stores(self):
        from core.isolation import assert_real
        for value in ({'nested':{'model_generated':True,'close':500}},prepare(rows5(),'IEX',NOW)['input_rows']):
            with self.assertRaisesRegex(ValueError,'MODEL_DATA_FORBIDDEN'):assert_real(value)
        with self.assertRaisesRegex(ValueError,'SIMULATED_DATA_FORBIDDEN'):assert_real({'quality':'SIMULATED'})
    def test_model_process_environment_excludes_credentials(self):
        with patch.dict('os.environ',{'APCA_API_SECRET_KEY':'fixture','OPENAI_API_KEY':'fixture','TELEGRAM_TOKEN':'fixture'}):
            env=environment();self.assertFalse(any('KEY' in k or 'TOKEN' in k for k in env));self.assertEqual(env['HF_HUB_OFFLINE'],'1')
    def test_model_resource_refusal_precedes_process_creation(self):
        with patch('subprocess.Popen',side_effect=AssertionError('must not launch')):
            self.assertEqual(bounded(['never'],{},memory=lambda:0)['status'],'BLOCKED_RESOURCE_HEADROOM')
    def test_model_timeout_and_malformed_child_do_not_block_parent(self):
        with tempfile.TemporaryDirectory() as d:
            script=Path(d)/'fixture.py';script.write_text('import sys,time\nsys.stdin.read()\ntime.sleep(3)\n');start=time.monotonic()
            r=bounded([sys.executable,str(script)],{},timeout=.3,memory=lambda:MINIMUM_FREE_BYTES,limit=128*1024*1024)
            self.assertIn(r['status'],('TIMEOUT','CONTAINMENT_OR_PROTOCOL_FAILED'));self.assertLess(time.monotonic()-start,3)
            script.write_text('import sys\nsys.stdin.read()\nprint("bad json")\n');r=bounded([sys.executable,str(script)],{},timeout=5,memory=lambda:MINIMUM_FREE_BYTES,limit=128*1024*1024);self.assertEqual(r['status'],'CONTAINMENT_OR_PROTOCOL_FAILED')
    def test_future_rows_cannot_change_bound_input_hash(self):
        rows=rows5();request=prepare(rows,'IEX',NOW);before=request['input_sha256'];rows.append(dict(rows[-1],start_at=NOW.isoformat()))
        with self.assertRaises(ValueError):prepare(rows,'IEX',NOW)
        self.assertEqual(request['input_sha256'],before)
    def test_restart_read_time_does_not_duplicate_identical_shadow_trial(self):
        rows=rows5();first=prepare(rows,'IEX',NOW)
        for row in rows:row['received_at']=(NOW+timedelta(seconds=1)).isoformat()
        again=prepare(rows,'IEX',NOW+timedelta(seconds=1));self.assertEqual(first['id'],again['id']);self.assertNotEqual(first['input_sha256'],again['input_sha256'])
if __name__=='__main__':unittest.main()
