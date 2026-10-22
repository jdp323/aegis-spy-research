"""Full-day fake-clock research flow. Synthetic inputs never touch a real store."""
import copy,json,hashlib
from pathlib import Path
from datetime import datetime,timezone,timedelta
from core.storage import ROOT
from core.sessions import ET,market_session
from core.idea_config import DEFAULTS,SETUPS
from core.idea_service import tick,context,candidates,trend_line,preopen_text
from backtesting.idea_tracker import IdeaTracker,score_text
class MemoryStore:
    def __init__(self):self.data={};self.records={}
    def get(self,k,default=None):return copy.deepcopy(self.data.get(k,default))
    def put(self,k,v):self.data[k]=copy.deepcopy(v)
    def event(self,k,kind,v):
        if k in self.records:return False
        self.records[k]=(kind,copy.deepcopy(v));return True
    def events(self,kind,limit=1000):return [v for k,v in self.records.values() if k==kind][-limit:]
def config():return {**DEFAULTS,'setup_enabled':{k:True for k in SETUPS},'signals':{'shared':False},'signal_expiry_seconds':600,'min_dte':1,'options_risk':{'max_trade_premium_usd':500},'notifications':{'categories':{'ideas':True,'idea_updates':True,'morning':True,'trend_lines':True}}}
def inputs(store,now,scenario='normal',rows=None):
    day=now.astimezone(ET).date();start=datetime.combine(day,datetime.min.time(),ET)+timedelta(minutes=570);count=max(0,int((now-start).total_seconds()/60));rows=[] if rows is None else rows
    while len(rows)<count:
        m=len(rows);px=500+.012*m if m<15 else 501+.012*(m-15)
        if scenario=='choppy':px=500+(.08 if m%2 else -.08)
        if scenario=='several':px=500+.015*m+(.8 if (m//3)%2 else -.8)
        if scenario=='down':px=1000-px
        rows.append({'t':(start+timedelta(minutes=m)).astimezone(timezone.utc).isoformat(),'o':px-.02,'h':px+.05,'l':px-.05,'c':px,'v':2500 if m%(3 if scenario=='several' else 15)==0 else 1000,'feed_quality':'SIMULATED'})
    price=rows[-1]['c']+.01 if rows else 500
    from data.replay import ReplayProvider
    provider=ReplayProvider(rows,{'bid':price-.01,'ask':price+.01,'mid':price},{},now)
    q=provider.get_underlying_quote().view(now);q.update(feed_quality='SIMULATED',source_timestamp=(now-timedelta(seconds=42) if scenario=='stale' and 630<=now.astimezone(ET).hour*60+now.astimezone(ET).minute<690 else now).isoformat())
    store.put('quote:SPY',q);store.put('stream_bars:SPY',rows);store.put('features',{})
    store.put('premarket_report:'+day.isoformat(),{'quality':'SIMULATED','bias':'UP','levels':{'last':500,'gap_pct':.2,'high':501,'low':499},'prior':{'close_proxy':499,'high':500,'low':498}})
    return rows
def run_scenario(name,day,start_minute=555,restart=False):
    store=MemoryStore();tracker=IdeaTracker(simulation=True);c=config();messages=[];rows=[]
    news={'quality':'DATA_OK','risk':'NORMAL','verified_at':datetime.combine(day,datetime.min.time(),ET).astimezone(timezone.utc).isoformat(),'events':[],'feed_quality':'SIMULATED'}
    end=market_session(datetime.combine(day,datetime.min.time(),ET)+timedelta(minutes=600))['close_minute']+20
    stale_seen=False
    for minute in range(start_minute,end):
        now=(datetime.combine(day,datetime.min.time(),ET)+timedelta(minutes=minute)).astimezone(timezone.utc)
        rows=inputs(store,now,'choppy' if name=='choppy' else 'stale' if name=='stale' else 'several' if name=='several' else 'normal',rows)
        if name in ('outage_backfill','opening_recovered','opening_unrecoverable','pc_pause'):
            capture=list(rows);q=store.get('quote:SPY')
            if name in ('outage_backfill','opening_recovered') and minute<684:
                q['source_timestamp']=(now-timedelta(seconds=300)).isoformat();capture=[]
            elif name=='opening_unrecoverable':capture=rows[15:]
            elif name=='pc_pause' and 720<=minute<740:
                q['source_timestamp']=(now-timedelta(seconds=120)).isoformat();capture=[r for r in rows if datetime.fromisoformat(r['t']).astimezone(ET).hour*60+datetime.fromisoformat(r['t']).astimezone(ET).minute<720]
            if name in ('outage_backfill','opening_recovered') and minute>=684:capture=[dict(r,source='REST_BACKFILL') for r in capture]
            store.put('quote:SPY',q);store.put('stream_bars:SPY',capture)
        # In-memory genuine simulation gate verifies simulated source age as well.
        if name=='several' and minute==660:
            for n in range(3):tracker.append({'signal_id':'loss-fixture-'+str(n),'status':'CLOSED','setup_type':'VWAP_RECLAIM','early':False,'r_multiple':-1,'closed_at':now.isoformat(),'timestamp':now.isoformat(),'feed_quality':'SIMULATED'},'FIXTURE_LOSS',now)
        if name=='several' and minute==605:
            for n in range(50):tracker.append({'signal_id':'negative-fixture-'+str(n),'status':'CLOSED','setup_type':'VWAP_RECLAIM','early':False,'r_multiple':-1,'closed_at':now.isoformat(),'timestamp':now.isoformat(),'feed_quality':'SIMULATED'},'FIXTURE_NEGATIVE',now)
        def publish(event):
            assert event['kind']=='RESEARCH' and event['tenant']=='owner' and event['audience']=='PRIVATE'
            assert len(event['text'])<3500
            messages.append({**event,'at_et':now.astimezone(ET).isoformat(),'simulation':True})
        tick(store,news,c,now,publish,tracker=tracker,simulation=True)
        if restart and minute==720:
            # New process facade retains the exact durable state, not a fresh schedule.
            replacement=MemoryStore();replacement.data=copy.deepcopy(store.data);replacement.records=copy.deepcopy(store.records);store=replacement
            tick(store,news,c,now,publish,tracker=tracker,simulation=True)
    session=market_session(datetime.combine(day,datetime.min.time(),ET)+timedelta(minutes=600));trends=[e for e in messages if e['alert_type']=='TREND_LINE'];pre=[e for e in messages if e['alert_type']=='PREOPEN'];recap=[e for e in messages if e['alert_type']=='RECAP']
    ids=[e['id'] for e in messages];assert len(ids)==len(set(ids)),'duplicate after restart'
    trading=session['active']
    if not trading:assert not messages,'non-trading messages'
    else:
        assert len(pre)==(1 if start_minute<=559 else 0)
        assert len(recap)==1
        assert all(e['disable_notification'] for e in trends)
        expected=[m for m in range(max(585,start_minute//15*15),session['close_minute']-14,15)]
        if True:
            assert len(trends)==len(expected),(name,len(trends),len(expected))
            assert [datetime.fromisoformat(e['at_et']).hour*60+datetime.fromisoformat(e['at_et']).minute//15*15 for e in trends]==expected,'wrong trend slots'
        assert all(585<=datetime.fromisoformat(e['at_et']).hour*60+datetime.fromisoformat(e['at_et']).minute<=session['close_minute']-15 for e in trends)
    controls={k:sum(p.get('alert_blocker')==k or k in p.get('additional_alert_blockers',[]) for p in tracker.positions()) for k in ('DIRECTION_COOLDOWN','COOL_OFF','NEGATIVE_EVIDENCE','RUNAWAY_BREAKER')}
    if name=='several':
        assert controls['DIRECTION_COOLDOWN']>0,'cooldown case absent'
        assert controls['NEGATIVE_EVIDENCE']>0,'negative suppression case absent: '+str(controls)+'; setups '+str(tracker.summary(now)['setups'])
        assert any('COOL-OFF' in e['text'] for e in messages),'cooloff warning absent'
    return {'name':name,'date':day.isoformat(),'PASS':True,'message_counts':{k:sum(e['alert_type']==k for e in messages) for k in sorted({e['alert_type'] for e in messages})},'control_decisions':controls,'timeline':messages,'score':tracker.summary((datetime.combine(day,datetime.min.time(),ET)+timedelta(minutes=end)).astimezone(timezone.utc)),'scope':'ReplayProvider plus real scheduler/context/setup/tracker/formatter; memory stores and fake transport. Several scenario seeds 3+50 explicitly synthetic loss records to stress cooloff and negative suppression; not market evidence.'}
def verify(root=ROOT):
    cases=[('normal','2026-10-09',555,False),('choppy','2026-10-09',555,False),('several','2026-10-09',555,False),('stale','2026-10-09',555,False),('late_restart','2026-10-09',667,True),('weekend','2026-10-10',555,False),('holiday','2026-11-26',555,False),('early_close','2026-11-27',555,False),('dst_week','2026-11-02',555,False),('2027_regular','2027-01-04',555,False),('2027_holiday','2027-11-25',555,False),('2027_early_close','2027-11-26',555,False)]
    results=[]
    for n,d,m,r in cases:
        try:results.append(run_scenario(n,datetime.fromisoformat(d).date(),m,r))
        except (AssertionError,ValueError) as error:
            out=Path(root)/'research';out.mkdir(exist_ok=True);p=out/('SCHEDULE_FAILED_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json')
            p.write_text(json.dumps({'status':'FAIL','scenario':n,'date':d,'reason':str(error),'completed_scenarios':results,'tag':'SIMULATED — failed experiment, not market evidence'},indent=2),encoding='utf-8');raise
    from ops.v6_simulation import cases as v6_cases
    results.extend(v6_cases())
    now=datetime.now(timezone.utc);out=Path(root)/'research';out.mkdir(exist_ok=True);base=out/('SCHEDULE_VERIFICATION_'+now.strftime('%Y%m%dT%H%M%SZ'));data={'at':now.isoformat(),'status':'PASS','tag':'TESTED — SIMULATED; not live delivery or edge','scenarios':results}
    import subprocess,sys
    directory=out/'verification/schedule_transports'/base.name
    directory.mkdir(parents=True,exist_ok=True)
    node=Path(__import__('core.runtime_paths',fromlist=['node_executable']).node_executable())
    transport=subprocess.run([str(node),'ops/schedule_transport.cjs'],cwd=root,input=json.dumps({'scenarios':results,'directory':str(directory.resolve())}),capture_output=True,text=True,encoding='utf-8',timeout=60)
    data['notifier_transport']=json.loads(transport.stdout)
    if transport.returncode or data['notifier_transport']['status']!='PASS':
        data['status']='FAIL';base.with_suffix('.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
        raise ValueError('SCHEDULE_FAKE_TRANSPORT_FAILED:'+str(data['notifier_transport']))
    base.with_suffix('.json').write_text(json.dumps(data,indent=2),encoding='utf-8');lines=['# V6 schedule verification','',data['tag'],json.dumps(data['notifier_transport']),'']
    for r in results:
        lines+=['## '+r['name']+' · '+r['date'],json.dumps(r['message_counts']),'']
        for e in r['timeline']:lines+=['### '+e['at_et']+' · '+e['alert_type']+' · '+('SILENT' if e['disable_notification'] else 'SOUND'),'```text','EXAMPLE — SIMULATED DATA',e['text'],'```','']
    base.with_suffix('.md').write_text('\n'.join(lines),encoding='utf-8');return base.with_suffix('.md'),data
if __name__=='__main__':print(verify()[0])
