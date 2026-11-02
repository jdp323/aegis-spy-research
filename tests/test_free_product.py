"""Free-mode product boundaries; synthetic stores/transports, never real sends."""
import copy,json,tempfile,unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from core.market_view import build,details,recap_view
from core.primary_plan import current,reserve,close_due_unresolved,administrative_end,public_state
from core.storage import Store
from core.idea_service import tick
from core.directional_research import record
from backtesting.idea_tracker import IdeaTracker
from ops.day_simulation import MemoryStore,config
from monitoring.owner_messages import status_text,premarket_text,idea_text,update_text,recap_text
from test_complete_telegram_messages import context,idea,NOW

NEWS={'quality':'DATA_OK','risk':'NORMAL','events':[]}

class FreeProduct(unittest.TestCase):
    def plan(self):
        return dict(idea(),entry_mode='ENTER NOW',entry_condition='completed 1-minute close above SPY $499.50',status='OPEN',alerted=True,do_not_chase=500.25,confirmation_at=NOW.isoformat(),coverage_status='UNRESOLVED_GAP')

    def test_stale_quote_preserves_bounded_trend_but_not_entry_or_scenario(self):
        c=context();c['reason']='SOURCE_TOO_OLD';c['quote']['source_timestamp']=(NOW-timedelta(seconds=6)).isoformat()
        s=build(c,NEWS,NOW);self.assertEqual(s['trend']['state'],'UP');self.assertFalse(s['entry']['underlying_eligible']);self.assertTrue(all(v['bias']=='ABSTAIN' for v in s['outlooks'].values()))
        message=status_text(c,NOW,NEWS);self.assertIn('UP through 11:00 ET completed candle',message);self.assertIn('fresh price unavailable',message);self.assertEqual(len(message.splitlines()),8)

    def test_stale_or_prior_session_synthetic_or_unavailable_bar_is_not_current(self):
        for mutate in ('stale','prior','synthetic','continuity','future_available'):
            c=context()
            if mutate=='stale':at=NOW+timedelta(seconds=121)
            else:at=NOW
            if mutate=='prior':
                for b in c['bar_research']['bars']:b['timestamp']-=86400
            if mutate=='synthetic':c['bar_research']['bars'][-1]['synthetic']=True
            if mutate=='continuity':c['bar_research']['bars'][-1]['continuity_only']=True
            if mutate=='future_available':c['bar_research']['bars'][-1]['available_at']=(NOW+timedelta(seconds=1)).isoformat()
            s=build(c,NEWS,at);self.assertEqual(s['trend']['state'],'UNAVAILABLE',mutate)

    def test_exact_fifteen_minute_endpoint_and_gap_required(self):
        c=context();c['bar_research']['bars']=c['bar_research']['bars'][-15:];self.assertEqual(build(c,NEWS,NOW)['trend']['state'],'UNAVAILABLE')
        c=context();c['bar_research']['bars'][-2]['timestamp']-=1;self.assertEqual(build(c,NEWS,NOW)['trend']['state'],'UNAVAILABLE')

    def test_h60_is_conditional_h120_session_are_not_copies(self):
        s=build(context(),NEWS,NOW);self.assertEqual(s['outlooks']['H60']['bias'],'UP');self.assertEqual(s['outlooks']['H120']['bias'],'ABSTAIN');self.assertEqual(s['outlooks']['SESSION']['bias'],'ABSTAIN')
        self.assertEqual(s['outlooks']['H60']['rule_version'],'h60-vwap-condition-v3-free');self.assertIn('conditional',details(s).lower())

    def test_h60_five_minute_disagreement_is_not_copied_current_uptrend(self):
        c=context();bars=c['bar_research']['bars']
        for row in bars[-5:]:row['close']-=.08
        s=build(c,NEWS,NOW)
        self.assertEqual(s['trend']['state'],'UP');self.assertEqual(s['outlooks']['H60']['bias'],'MIXED')

    def test_automatic_admin_end_releases_only_public_slot_and_deduplicates(self):
        s=MemoryStore();p=self.plan();before=copy.deepcopy(p);reserve(s,p,NOW);s.put('research-pause:v2',{'seen':['loss1'],'episode':{'id':'unchanged'}})
        s.put('private-fixture',{'quantity':1,'contract':'FICTIONAL'})
        self.assertFalse(close_due_unresolved(s,[p],administrative_end(p)-timedelta(seconds=1)))
        result=close_due_unresolved(s,[p],administrative_end(p));self.assertEqual(len(result),1);self.assertIsNone(current(s,[p],administrative_end(p)))
        self.assertEqual(p,before);self.assertFalse(result[0][1]['observed_exit']);self.assertIsNone(result[0][1]['pnl']);self.assertEqual(s.get('private-fixture')['quantity'],1)
        self.assertEqual(s.get('research-pause:v2')['seen'],['loss1']);self.assertFalse(close_due_unresolved(s,[p],administrative_end(p)+timedelta(days=1)))
        self.assertEqual(len(s.events('primary_admin_closure')),1)

    def test_atomic_admin_event_index_survive_reopen_without_outcome_rewrite(self):
        p=self.plan();p['feed_quality']='IEX'
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'s.sqlite';s=Store(path);reserve(s,p,NOW);close_due_unresolved(s,[p],administrative_end(p));s.close()
            s=Store(path);self.assertIsNone(current(s,[p],administrative_end(p)));self.assertEqual(len(s.events('primary_admin_closure')),1);self.assertFalse(close_due_unresolved(s,[p],administrative_end(p)));s.close()
        self.assertEqual(p['status'],'OPEN');self.assertEqual(p['coverage_status'],'UNRESOLVED_GAP')

    def test_public_state_does_not_claim_a_personal_purchase_or_sale(self):
        p=self.plan();self.assertEqual(public_state(p,NOW,False),'COVERAGE UNKNOWN')
        p['coverage_status']='COMPLETE_SO_FAR';self.assertEqual(public_state(p,NOW,True),'MONITORING')
        p.update(status='EXPIRED_NO_ENTRY');self.assertEqual(public_state(p,NOW),'ENTRY EXPIRED')
        self.assertNotIn('sold',update_text(p,'ADMIN_CLOSED_UNRESOLVED').lower())

    def test_carryover_recap_and_retired_unknown_count_separate(self):
        old=self.plan();old['timestamp']=(NOW-timedelta(days=1)).isoformat()
        today=self.plan();today['signal_id']='b'*24
        closures=[{'signal_id':old['signal_id'],'at':NOW.isoformat()},{'signal_id':today['signal_id'],'at':NOW.isoformat()}]
        r=recap_view([old,today],NOW,closures);self.assertEqual(r['alerted'],1);self.assertEqual(r['carried_in'],1);self.assertEqual(r['unresolved'],1);self.assertEqual(r['open'],0);self.assertEqual(r['administratively_closed_unresolved'],1)
        self.assertIn('1 carried in',recap_text([old,today],NOW,'UNAVAILABLE',snapshot={'recap':r}))

    def test_all_default_message_contracts_are_bounded_and_unavailable_honest(self):
        p=self.plan();texts=[premarket_text({},NEWS,NOW),status_text(context(),NOW,NEWS,plan=p),idea_text(p,{},{}),update_text(p,'STOP_HIT'),recap_text([p],NOW,'UNAVAILABLE')]
        for text,cap in zip(texts,(8,8,9,2,8)):
            self.assertLessEqual(len(text.splitlines()),cap);self.assertLess(len(text),3500);self.assertNotIn("{'",text);self.assertNotIn('None',text);self.assertNotIn('BUY THIS',text)
        self.assertIn('opening range not known yet',texts[0]);self.assertIn('reference',texts[2]);self.assertIn('option contract unavailable',texts[2])

    def test_fast_tick_does_not_execute_slow_research_and_parent_update_stays_anchored(self):
        s=MemoryStore();t=IdeaTracker(simulation=True);p=dict(self.plan(),feed_quality='SIMULATED');t.append(p,'REGISTER',NOW);reserve(s,p,NOW)
        at=administrative_end(p);events=[]
        c=context();c.update(rows=[],early=False,horizons={});c['bar_research']['rows']=[]
        with patch('core.idea_service.context',return_value=c),patch('core.idea_service.candidates',return_value=([],None)),patch('core.idea_service.maintenance_research',side_effect=AssertionError('slow study entered fast path')):
            tick(s,NEWS,config(),at,events.append,tracker=t,simulation=True,fast=True)
        update=next(e for e in events if 'ADMIN_CLOSED_UNRESOLVED' in e['id']);self.assertEqual(update['parent_event_id'],'v5-idea-'+p['signal_id']+'-'+p['strategy_version']);self.assertEqual(update['audience'],'PRIVATE');self.assertEqual(len(s.events('primary_admin_closure')),1)

    def test_forecast_metadata_matches_actual_reference_and_new_rule_version(self):
        s=MemoryStore();snapshot=build(context(),NEWS,NOW)
        value=record(s,'fixture',NOW,{'outlooks':snapshot['outlooks'],'reference_rule':'ISSUE_TIME_FRESH_QUOTE_MIDPOINT','as_of':NOW.isoformat()},'H60')
        self.assertEqual(value['reference_rule'],'ISSUE_TIME_FRESH_QUOTE_MIDPOINT');self.assertEqual(value['version'],'h60-vwap-condition-v3-free');self.assertIn('MATCHING_FEED_QUOTE',value['outcome_rule']);self.assertFalse(value['calibrated'])

if __name__=='__main__':unittest.main()
