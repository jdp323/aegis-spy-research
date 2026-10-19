"""V5 read-only packet extension; allowlisted aggregate evidence, no vault access."""
import json
from pathlib import Path
def extend(packet,root,now):
    from ops.verification_packet import read_json,sha,database,ro
    from ops.hygiene import check
    from ops.demo import v5_scene
    root=Path(root);packet['header']['prompt']='V5 SPY ideas, schedule, commands and honest outcomes'
    packet['deployment_observations']['V5_real_Telegram_development_messages']=0
    packet['deployment_observations']['V5_guest_development_messages']=0
    packet['deployment_observations']['owner_TEST_receipt_scope']='Historical V3/V4 saved receipt; no V5 real message sent or phone delivery claimed.'
    shared=read_json(root/'config/upgrade.json',{}).get('signals',{}).get('shared') is True
    packet['safety']['guest_routing']=('Public automatic research shared with approved users; signals.shared=true. ' if shared else 'New automatic messages owner-only; signals.shared=false. ')+ 'Fill ledgers and personal/admin replies private; existing owner-only callbacks unchanged. Uncertain delivery never replayed.'
    packet['v5']={'schedule':{'timezone':'America/New_York','preopen':'09:15','trend':'09:45–15:45, current 15-minute slot only; silent','recap':'16:15; early close +15 minutes','early_close_last_trend':'close minus 15 minutes','restart':'Durable reservation before outbox; uncertain delivery never blindly replayed','expiry':'600 seconds; actual trigger and outcome lifecycle separate'},'database_hygiene':check(root),'commands':{},'schedule_verification':{},'idea_tracker':database(root/'runtime/ideas.sqlite'),'evidence':'NOT VALIDATED; underlying share outcomes are not option P&L','calendar_import':'Owner-attested official file hash; not independent origin proof; download age does not reset','FRED':'Optional encrypted key; absent skipped; date-only supplement cannot replace issuer coverage; HIGH date-only creates full-day blackout','limits':'Old option/proxy paper caps unchanged. New idea alert cap null, breaker 40/day, direction cooldown 10m, three losses cooloff 60m.'}
    for prefix,key in [('COMMAND_VERIFICATION_','commands'),('SCHEDULE_VERIFICATION_','schedule_verification')]:
        paths=sorted((root/'research').glob(prefix+'*.json'))
        if not paths:packet['v5'][key]={'status':'NOT DONE'};continue
        p=paths[-1];data=read_json(p,{})
        info={'path':str(p.with_suffix('.md').relative_to(root)),'json_sha256':sha(p),'status':data.get('status'),'at':data.get('at')}
        if key=='commands':
            rows=data.get('rows',[]);info.update(command_count=data.get('command_count'),cases=len(rows),passed=sum(x['result']=='PASS' for x in rows),failed=sum(x['result']!='PASS' for x in rows),menu=data.get('menu'),limitations=data.get('limitations'),rows=[{'command':name,'role':role,'arguments':'valid / missing / invalid','results':[r['result'] for r in rows if r['command']==name and r['role']==role],'EXAMPLE_excerpt':next((r['reply_excerpt'][:100] for r in rows if r['command']==name and r['role']==role),'UNAVAILABLE')} for name in sorted({r['command'] for r in rows}) for role in ('owner','guest','stranger')])
        else:info.update(scenarios=[{'name':r['name'],'date':r['date'],'PASS':r['PASS'],'counts':r['message_counts'],'timeline_events':len(r['timeline']),'first_lines_EXAMPLE':[{'at_et':e['at_et'],'type':e['alert_type'],'text':'\n'.join(e['text'].splitlines()[:3])} for e in r['timeline'][:3]],'scope':r['scope']} for r in data.get('scenarios',[])],notifier_transport=data.get('notifier_transport'),limitation='Synthetic fake-clock, memory stores and fake transport; not live delivery or market edge. Full labelled timeline retained in hashed report.')
        packet['v5'][key]=info
    p=root/'runtime/ideas.sqlite'
    if p.exists():
        from backtesting.idea_tracker import IdeaTracker
        tracker=IdeaTracker.__new__(IdeaTracker);tracker.simulation=False;tracker.memory=[];tracker.db=ro(p)
        try:packet['v5']['scoreboard']=tracker.summary(now)
        finally:tracker.close()
    else:packet['v5']['scoreboard']={'state':'NO_DATABASE_YET','closed':0,'evidence_tag':'INSUFFICIENT DATA'}
    packet['samples_EXAMPLE'].update({key:'EXAMPLE — SIMULATED DATA\n'+v5_scene('call',stage) for key,stage in [('preopen_V5',0),('early_read_V5',1),('trend_V5',2),('idea_V5',3),('entry_V5',4),('target_V5',5),('stop_V5',6),('expired_V5',7),('recap_V5',8),('score_V5',9)]})
    packet['migration_notes']['idea_schema']=1;packet['migration_notes']['idea_strategy']='spy-ideas-v1 / spy-ideas-v1-early';packet['migration_notes']['idea_scoring']='idea-check-count-v1: five mandatory checks; not probability';packet['migration_notes']['idea_table']='runtime/ideas.sqlite idea_events, append-only; no existing ledger migration'
    charts=sorted((root/'daily_reports/charts').glob('demo-console-*.png'))
    packet['v5']['demo_chart_hashes']={p.name:sha(p) for p in charts}
    packet['v5']['demo_charts_distinct']=len(charts)==4 and len({sha(p) for p in charts})==4
    runtime=read_json(root/'research/V5_RUNTIME_CHECK.json',{})
    packet['v5']['runtime_check']={
        'path':'research/V5_RUNTIME_CHECK.json','sha256':sha(root/'research/V5_RUNTIME_CHECK.json') if runtime else None,
        'at':runtime.get('at'),'dashboard_http':runtime.get('dashboard_http'),
        'supervisor_heartbeat_age_seconds':runtime.get('services',{}).get('heartbeat_age_seconds'),
        'components':{k:{field:v.get(field) for field in ('state','process_alive','restarts')} for k,v in runtime.get('services',{}).get('components',{}).items()},
        'health':{k:{field:v.get(field) for field in ('at','state','reason','feed_quality','offset_seconds')} for k,v in runtime.get('health',{}).items() if isinstance(v,dict)},
        'listener':{k:runtime.get('listener',{}).get(k) for k in ('at','state')},
        'dispatcher':{k:runtime.get('dispatcher',{}).get(k) for k in ('at','state')},
        'pending_requests':runtime.get('pending_request_files'),
        'scope':'Dated process/heartbeat check only. Closed session cannot prove quote freshness, idea delivery or edge.'}
    packet['weak_points']+=['Many higher-frame trends lack history; UNAVAILABLE is never an affirmative alignment vote.','All confirmed ideas have five mandatory checks; A+ is not evidence of success.','Overlapping ideas and retrospective sample intervals are correlated; no random-entry edge proof for the new tracker.','Runaway/cooloff gates are alert controls, not a maximum option loss guarantee.','Timed calendar imports require honest owner attestation. FRED is date-only and missing optional events remain unknown.']
