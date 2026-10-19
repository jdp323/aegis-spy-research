"""Allowlisted V6 packet additions; no network, vault or brokerage access."""
import json,sqlite3
from core.sessions import ET
from ops.session_report import collect
def extend(packet,root,now):
    from ops.verification_packet import read_json,database,sha
    backup=read_json(root/'research/v6_backup.json',{}) or {}
    packet['header'].update(prompt='V6 capture, truthfulness and observability',backup=backup.get('backup'))
    packet['migration_notes'].update(idea_schema=2,idea_strategy='spy-ideas-v2-observed',idea_baseline='idea_baseline_events, separate append-only random-direction matched-clock population',observability='stream_events, rejection_traces, bar_confirmations, backfill_runs; additive',forward_counters='forward_reason_counts, per minute/reason/version; blank evaluations never become new evidence')
    packet['gates_before']=backup.get('gates_before',{})
    packet['safety']['guest_routing']='signals.shared remains true. Production shared research follows existing authorized membership; development transports are fake and never send to guests. Owner-only outage/delivery warnings stay private.'
    packet['safety']['storage_queries']='mode=ro/query_only SELECTs including committed WAL; no operational rows changed. Cross-database snapshots are not one transaction.'
    packet['migration_notes']['idea_scoring']='idea-check-count-v2-observed; same existing confirmation thresholds, measured diagnostics and versioned message behavior'
    packet['deployment_observations']['V6_real_Telegram_development_messages']=0
    packet['deployment_observations']['V6_guest_development_messages']=0
    from monitoring.sharing import display
    packet['sharing_VERIFIED']=display(packet['config_VERIFIED'],root)
    # Complete evidence lives in hashed reports. Avoid repeating 105 excerpts and
    # every simulation's first messages in the bounded review packet.
    commands=packet.get('v5',{}).get('commands',{})
    rows=commands.get('rows',[])
    commands['rows']=[{'command':name,'results_by_role':{role:next((r['results'] for r in rows if r['command']==name and r['role']==role),[]) for role in ('owner','guest','stranger')}} for name in sorted({r['command'] for r in rows})]
    for scenario in packet.get('v5',{}).get('schedule_verification',{}).get('scenarios',[]):scenario.pop('first_lines_EXAMPLE',None)
    for detail in packet.get('gaps',{}).values():
        if isinstance(detail,dict) and 'excerpt' in detail:detail['excerpt']=detail['excerpt'][-1500:];detail['scope']='Latest 1500 characters; full document is hashed and retained.'
    packet['v6']={'status':'IMPLEMENTED; external regular-session behavior requires new session evidence','backup_rows_before':backup.get('rows_before',{}),'rows_after':{str(p.relative_to(root)):database(p).get('tables',{}) for p in (root/'runtime/aegis.sqlite',root/'runtime/paper.sqlite',root/'runtime/ideas.sqlite',root/'runtime/history.sqlite',root/'runtime/observability.sqlite',root/'options/reported.sqlite')},'last_session':collect('2026-10-09',root,now),'retention':'Active views: stream 30 days, setup traces/reason counters 14 days; archival rows preserved.','configuration_changes':'No live flag, entitlement, freshness threshold or sharing changes. Reliability constants 90s reconnect/300s restart; REST finalize lag 120s/cooldown 300s; continuity maximum 2/31; definitive delivery max 3 total attempts; evidence labels min 50 closed ideas.','safety_proofs':['SIP/OPRA/live gates unchanged; IEX never passes those gates.','SIMULATED and continuity_only rejected recursively at real boundaries.','Only completely returned same-feed eligible aggregates can confirm bounded omissions.','No uncertain-after-send automatic retry; owner-only confirmation refuses guest receipts.','No guest development messages.','New diagnostics and separately tagged baselines are not trade validation.'],'ways_this_could_be_wrong':['IEX eligible prints can be sparse; complete higher-timeframe resampling can remain unavailable.','Provider backfill and next-session capture are not proved by synthetic tests.','REST aggregate revisions may arrive after the two-minute finalization lag.','Windows pause detection identifies scheduling gaps but cannot prove a physical sleep cause.','Telegram acceptance does not prove display on a phone.','Legacy failures lack exact predicates and cannot be recovered retrospectively.','Overlapping matched-clock baselines are correlated, so confidence intervals are heuristic.','A local machine offline cannot send its own outage warning; external heartbeat remains optional.']}
    for prefix,key in (('COMMAND_VERIFICATION_','commands'),('SCHEDULE_VERIFICATION_','schedule')):
        paths=sorted((root/'research').glob(prefix+'*.json'))
        if paths:
            p=paths[-1];d=read_json(p,{})
            packet['v6'][key]={'path':str(p.with_suffix('.md')),'sha256':sha(p),'status':d.get('status'),'cases':len(d.get('rows',d.get('scenarios',[]))),'failed':sum(r.get('result')!='PASS' for r in d.get('rows',[]))}
    paths=sorted((root/'research').glob('V6_RUNTIME_CHECK*.json'))
    if paths:packet['v6']['deployment']=read_json(paths[-1],{})
    packet['weak_points']=[w for w in packet['weak_points'] if 'no random-entry edge proof for the new tracker' not in w]+packet['v6']['ways_this_could_be_wrong']
