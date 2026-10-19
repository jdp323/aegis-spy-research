"""Additional V6 failure timelines, isolated fixtures and fake clocks only."""
from datetime import datetime,timezone,timedelta
import tempfile,json
from pathlib import Path
from core.sessions import ET
from data.reliability import PauseProbe,quote_diagnostics,describe,watchdog_age
from data.backfill import Backfill
from data.providers import AlpacaProvider
from ops.day_simulation import MemoryStore,config,run_scenario
def cases():
    results=[];day=datetime(2026,10,9).date()
    for name in ('outage_backfill','opening_recovered','opening_unrecoverable','pc_pause'):
        r=run_scenario(name,day);results.append(r)
    def result(name,entries):
        timeline=[{'id':'v6-fixture-'+name+'-'+str(n),'kind':'RESEARCH','audience':'PRIVATE','tenant':'owner','alert_type':'TREND_LINE','text':'EXAMPLE — SIMULATED DATA\n'+text,'expires_at':(at+timedelta(minutes=5)).isoformat(),'disable_notification':True,'at_et':at.astimezone(ET).isoformat(),'simulation':True} for n,(at,text) in enumerate(entries)]
        return {'name':name,'date':day.isoformat(),'PASS':True,'message_counts':{'TREND_LINE':len(timeline)},'timeline':timeline,'scope':'TESTED component fixtures, fake clocks/transport. Not actual provider access, guest delivery or market evidence.'}
    now=datetime(2026,10,9,10,0,tzinfo=ET).astimezone(timezone.utc)
    from data.models import quote
    valid=quote('alpaca-iex','SPY',{'t':now.isoformat(),'bp':500,'ap':500.02},received=now.isoformat()).view(now)
    entries=[]
    for name,over in [('receipt_after_clock',{'received_timestamp':(now+timedelta(seconds=.1)).isoformat()}),('source_stale',{'source_timestamp':(now-timedelta(seconds=7.2)).isoformat()}),('source_future',{'source_timestamp':(now+timedelta(seconds=.1)).isoformat()}),('provider_mismatch',{'provider':'wrong'}),('invalid_bid_ask',{'payload':{'bid':501,'ask':500}})]:
        d=quote_diagnostics({**valid,**over},now,'alpaca-iex');assert d['predicate'];entries.append((now,describe(d)))
    from core.observed_context import evaluate
    for health in ({'state':'CONNECTED','at':(now-timedelta(seconds=41)).isoformat()},{'state':'FEED_DISCONNECTED','at':now.isoformat()},{'state':'CONNECTED','at':now.isoformat()}):
        store=MemoryStore();store.put('research_quote:SPY:iex',valid);store.put('stream:iex',health);ctx=evaluate(store,now);assert ctx['reason'];entries.append((now,ctx['reason']))
    results.append(result('all_stale_predicates',entries))
    probe=PauseProbe();probe.check(now,10);pause=probe.check(now+timedelta(minutes=20),11);assert pause['duration_seconds']==1200
    results.append(result('pause_clock_diagnostics',[(now,'Normal heartbeat'),(now+timedelta(minutes=20),'PROCESS_PAUSED '+json.dumps(pause))]))
    # The complete provider-response/backfill path is exercised through an
    # injected transport in an isolated directory; inputs are labelled fixtures.
    with tempfile.TemporaryDirectory() as folder:
        opening=now.replace(hour=13,minute=30);rows=[{'t':(opening+timedelta(minutes=i)).isoformat(),'o':500,'h':500.1,'l':499.9,'c':500,'v':100} for i in range(115)]
        b=Backfill(Path(folder)/'fixture.sqlite',AlpacaProvider(lambda *args:{'bars':rows}));store=MemoryStore();out=b.run(store,opening+timedelta(minutes=116));assert out['status']=='DATA_OK';assert len(store.get('research_stream_bars:SPY:iex'))==115;b.close()
        results.append(result('rest_backfill_actual_adapter_fixture',[(opening,'Stream unavailable — missing opening range'),(opening+timedelta(minutes=114),'Fake complete same-feed REST response: '+str(out['bars'])+' original bars; no fabricated candles; source REST_BACKFILL')]))
    # Real formatter, zero-volume official-shape price fixture; no production store.
    from unittest.mock import patch
    from tests.test_premarket_brief import fixture,NOW
    from monitoring.premarket_brief import build,text_for
    raw=fixture(NOW)
    for bar in raw['bars']:bar['volume']=0
    with patch('monitoring.premarket_brief.verified',return_value=True):report=build(raw,now=NOW)
    assert report['quality']=='PUBLIC_RESEARCH_ONLY' and report['levels']['vwap_approx'] is None
    results.append(result('zero_volume_premarket',[(NOW,text_for(report))]))
    results.append(result('sharing_visibility',[(now,'signals.shared: ON (2 guests) — fixture membership count; no development guest send')]))
    import subprocess,sys
    node=Path(__import__('core.runtime_paths',fromlist=['node_executable']).node_executable())
    child=subprocess.run([str(node),str(Path(__file__).with_name('v6_notifier_sim.cjs'))],capture_output=True,text=True,timeout=30,check=True)
    failures=json.loads(child.stdout)
    results.append(result('notifier_failures_retry_and_uncertainty',[(now,json.dumps(r,sort_keys=True)) for r in failures]))
    # Independently versioned horizons are not stretched scalp observations.
    # Exercise their real cutoff function and generator against explicit fixtures.
    from core.research_horizons import deadline,candidates as horizon_candidates
    from tests.test_research_horizons import HorizonRules
    rules=HorizonRules();at,ctx,q=rules.fixture()
    variants=horizon_candidates(ctx,q,at)
    orb=[r for r in variants if r['setup_type']=='ORB_RETEST']
    assert len(orb)==6 and len({r['signal_id'] for r in orb})==6
    assert all(datetime.fromisoformat(r['signal_expiry'])<=datetime.fromisoformat(r['max_hold_until']) and r['actual_reported_fill'] is None and not r['live_signal_ready'] for r in orb)
    boundaries=[('2026-10-19','13:55','H120',True,'15:55'),('2026-10-19','13:56','H120',False,None),
                ('2026-10-19','15:25','SESSION',True,'15:55'),('2026-10-19','15:26','SESSION',False,None),
                ('2026-11-27','10:55','H120',True,'12:55'),('2026-11-27','10:56','H120',False,None),
                ('2027-01-04','10:45','H60',True,'11:45'),('2027-11-25','10:45','H60',False,None)]
    entries=[(at,'Six predeclared ORB_RETEST horizon/ATR variants retain distinct stable IDs and immutable trigger/reference/modeled-fill/actual-fill fields. All actual reported fills are unavailable; no live or option qualification.')]
    for date,clock,horizon,allowed,expected in boundaries:
        moment=rules.at(date,clock);end=deadline(moment,horizon)
        assert (end is not None)==allowed
        if expected:assert end.astimezone(ET).strftime('%H:%M')==expected
        entries.append((moment,horizon+' new observation '+('ALLOWED until '+end.astimezone(ET).strftime('%H:%M ET') if end else 'BLOCKED: full planned horizon/session cutoff not available')))
    assert deadline(rules.at('2026-11-02'),'H120').hour==17
    from tests.test_v5_ideas import seed,oq,NOW as fixture_now
    from backtesting.idea_tracker import IdeaTracker
    tracker=IdeaTracker(simulation=True)
    for changes,code in (({'max_hold_until':fixture_now.isoformat()},'DEADLINE'),({'signal_expiry':(fixture_now+timedelta(hours=2)).isoformat()},'VALIDITY')):
        idea=seed();idea.update(changes)
        try:tracker.register(idea,oq(),fixture_now)
        except ValueError as error:assert code in str(error)
        else:raise AssertionError('Expired/overlong entry validity was admitted')
    assert not tracker.positions()
    row=result('horizon_deadlines_and_price_identity',entries)
    row['date']=at.astimezone(ET).date().isoformat()
    row['scope']='TESTED component timelines across regular/early-close/holiday/DST/2027 sessions; pure generator and memory-only tracker. Fixtures never establish genuine option performance.'
    results.append(row)
    # The idea scheduler does not own these jobs: exercise the real reliability
    # scheduler separately, keeping the close+20 report local rather than adding
    # a synthetic Telegram broadcast at that time.
    from core.v6_service import Reliability
    from data.providers import UnconfiguredProvider
    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder);store=MemoryStore();clock=[rules.at('2026-10-19','09:20')];timeline=[];local_jobs=[]
        service=Reliability(store,UnconfiguredProvider(),root=root,clock=lambda:clock[0])
        def enqueue(_store,ident,text,audience,tenant,kind='RESEARCH',**metadata):
            assert audience=='PRIVATE' and tenant=='owner'
            timeline.append({'id':ident,'kind':kind,'audience':audience,'tenant':tenant,'alert_type':metadata.get('alert_type','DATA_WARNING'),'text':'EXAMPLE — SIMULATED DATA\n'+text,'expires_at':(clock[0]+timedelta(minutes=5)).isoformat(),'disable_notification':False,'at_et':clock[0].astimezone(ET).isoformat(),'simulation':True})
        try:
            service.tick(clock[0],enqueue);service.tick(clock[0],enqueue)
            assert len(timeline)==1 and timeline[0]['alert_type']=='DATA_WARNING'
            assert '09:20' in timeline[0]['text']
            with patch('ops.session_report.write',side_effect=lambda date,path:local_jobs.append({'date':date,'at_et':clock[0].astimezone(ET).isoformat(),'local_only':True})):
                for date,local_time in (('2026-10-19','16:20'),('2027-11-26','13:20')):
                    clock[0]=rules.at(date,local_time);service.tick(clock[0],enqueue);service.tick(clock[0],enqueue)
            assert len(local_jobs)==2 and len(timeline)==1
        finally:service.close()
    results.append({'name':'owner_precheck_and_local_session_report','date':'2026-10-19','PASS':True,'message_counts':{'DATA_WARNING':1},'timeline':timeline,'local_jobs':local_jobs,'scope':'Real Reliability.tick with fake clocks, MemoryStore, isolated telemetry, unconfigured provider and fake report writer; 09:20 owner warning dedupe plus close+20 local report on normal and 2027 early-close days. No close+20 Telegram message.'})
    return results
