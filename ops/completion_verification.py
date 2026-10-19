"""Safe evidence extension for the October17 completion request; no network/writes."""
import json,hashlib,re
from pathlib import Path
from datetime import datetime

SESSION_FIELDS=('schema_version','date_et','generated_at_utc','scope','LIVE_SIGNAL_READY','status','reasons','feed_quality','minute_coverage','outages','recorded_fraction','messages','idea_engine','frames','opening_range','clock_stream','limitations','retained_stream_gap_intervals','backfill_timing')

def read(path,default=None):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError):return default

def artifact(root,path):
    """A hash binds a summary to retained evidence; it does not verify its claims."""
    path=Path(path)
    if not path.is_file():return {'path':str(path.relative_to(root)),'status':'UNAVAILABLE'}
    body=path.read_bytes()
    return {'path':path.relative_to(root).as_posix(),'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body)}

def latest_session(root,now):
    """Use a completed verified session's saved report, preserving its as-of clock."""
    from core.sessions import ET,market_session
    for path in sorted((root/'daily_reports').glob('SESSION_REPORT_*.json'),reverse=True):
        match=re.fullmatch(r'SESSION_REPORT_(\d{4}-\d{2}-\d{2})\.json',path.name)
        if not match:continue
        try:
            day=datetime.fromisoformat(match[1]).replace(hour=12,tzinfo=ET)
            session=market_session(day)
            if not session.get('active') or day.replace(hour=session['close_minute']//60,minute=session['close_minute']%60)>now:continue
            report=read(path,{})
            if report.get('date_et')!=match[1] or report.get('status')=='NO_SESSION':continue
        except (ValueError,KeyError,TypeError):continue
        from ops.verification_packet import scan
        if scan(json.dumps(report,ensure_ascii=False)):raise ValueError('COMPLETION_SESSION_SECRET_REJECTED')
        summary={key:report[key] for key in SESSION_FIELDS if key in report}
        return {'artifact':artifact(root,path),'date_et':match[1],'saved_report_generated_at_utc':report.get('generated_at_utc'),'scope':'Retained report as of its original generation time; retrospective repairs and latest clock/config observations do not establish contemporaneous session availability.','report':summary}
    return {'status':'UNAVAILABLE','reason':'No retained report for a completed verified trading session.'}

def compact_historical_duplicates(packet,root,command,schedule):
    """Keep evidence and hashes; omit duplicated per-role rows and old examples."""
    from ops.verification_packet import scan
    # Preserve refusal for secrets in a section before replacing it with a hash.
    # Section bounds are smaller than the existing packet scanner input bound.
    for name in ('v5','samples_EXAMPLE','gaps'):
        body=json.dumps(packet.get(name,{}),ensure_ascii=False,allow_nan=False)
        if len(body.encode('utf-8'))>150000:raise ValueError('PACKET_SECTION_TOO_LARGE')
        if scan(body):raise ValueError('PACKET_REFUSED_SECRET_PATTERN')
    v5=packet.get('v5',{})
    commands=v5.get('commands',{})
    if commands:
        v5['commands']={k:commands[k] for k in ('status','at','command_count','cases','passed','failed','limitations') if k in commands}
        v5['commands'].update(evidence=artifact(root,command) if command else {'status':'UNAVAILABLE'},scope='Full role/argument replies retained in the hashed command artifact; current summary is in completion.command_verification.')
    schedules=v5.get('schedule_verification',{})
    if schedules:
        cases=schedules.get('scenarios',[])
        v5['schedule_verification']={'status':schedules.get('status'),'scenario_count':len(cases),'passed':sum(bool(r.get('PASS')) for r in cases),'failed':sum(not bool(r.get('PASS')) for r in cases),'evidence':artifact(root,schedule) if schedule else {'status':'UNAVAILABLE'},'scope':'Full fake-clock timelines remain in the hashed artifact; they do not prove live capture or delivery.'}
    samples=packet.get('samples_EXAMPLE',{})
    keep=('call_guideline_EXAMPLE','put_specific_EXAMPLE_SIMULATED','no_trade_EXAMPLE','closed_EXAMPLE','paper_EXAMPLE','exit_EXAMPLE')
    packet['samples_EXAMPLE']={k:samples[k] for k in keep if k in samples}
    packet['samples_EXAMPLE']['scope']='Historical generated fixture examples only. Current message formats are in the hashed current_message_reference.'
    packet['samples_EXAMPLE']['current_message_reference']=artifact(root,root/'TELEGRAM_MESSAGE_EXAMPLES.md')
    packet['gaps']={name:{'artifact':artifact(root,root/'research'/name),'scope':'Full dated document retained; current blocker/action conclusions are in the completion handoff.'} for name in packet.get('gaps',{})}
    if 'last_session' in packet.get('v6',{}):
        historical=packet['v6'].pop('last_session')
        packet['v6']['historical_session_2026-10-09']={'scope':'Historical session, retrospectively inspected now; not the latest session. Previously issued packets remain unchanged.','report':historical}

def extend(packet,root,now):
    from ops.verification_packet import manifest,database,scan
    root=Path(root);folder=root/'research/completion_verification'
    backup=read(root/'research/completion_backup.json',{})
    packet['header'].update(prompt='Complete implementation, testing and operational verification; strict research-only scope',backup=backup.get('backup'))
    packet['change_manifest']=manifest(root,backup.get('backup'))
    final=read(folder/'final/latest_tests.json')
    # --run-tests may have just produced a newer result in verification/.
    # Never replace that run with an older saved completion-suite result.
    current=packet.get('tests') or {}
    def checked(result):
        try:
            value=datetime.fromisoformat(result['checked_at'])
            return value.timestamp() if value.tzinfo is not None else float('-inf')
        except (KeyError,ValueError,TypeError):return float('-inf')
    if final and checked(final)>=checked(current):packet['tests']=final
    if packet.get('tests'):packet['test_claim']='Latest dated completed isolated suite result; named checks only. No live-session/option entitlement inference.'
    def latest(pattern):
        files=sorted((root/'research').glob(pattern));return files[-1] if files else None
    command=latest('COMMAND_VERIFICATION_*.json');schedule=latest('SCHEDULE_VERIFICATION_*.json')
    c=read(command,{}) if command else {};s=read(schedule,{}) if schedule else {}
    report={
        'at':now.isoformat(),'classification_vocabulary':['VERIFIED IN OPERATION','TESTED IN ISOLATION','IMPLEMENTED, EXTERNAL VERIFICATION PENDING','BLOCKED','DEFERRED OUTSIDE CORE SCOPE'],
        'backup':backup,'restoration':read(folder/'RESTORE_VERIFICATION.json',{'status':'NOT_DONE'}),
        'baseline':read(folder/'baseline/BASELINE_RESULTS.json',{}).get('result',{}),
        'market_probe':read(folder/'MARKET_DATA_PROBE.json',{'status':'EXTERNAL_VERIFICATION_PENDING'}),
        'service_operation':read(folder/'SERVICE_OPERATION.json',{'status':'EXTERNAL_VERIFICATION_PENDING'}),
        'command_verification':{'path':str(command) if command else None,'status':c.get('status','PENDING'),'command_count':c.get('command_count'),'cases':len(c.get('rows',[])),'roles':sorted({r['role'] for r in c.get('rows',[])})},
        'schedule_verification':{'path':str(schedule) if schedule else None,'status':s.get('status','PENDING'),'scenarios':[r.get('name') for r in s.get('scenarios',[])],'transport':s.get('notifier_transport')},
        'exchange_calendar_provenance':read(root/'research/calendar_sources/exchange_verification.json',{}),
        'research_reproduction':read(root/'research/RESEARCH_REPRODUCTION.json',{'status':'See frozen research manifest; no option-performance inference.'}),
        'separate_populations':['Legacy V5/V6 underlying ideas','H60/H120/SESSION underlying comparison observations','Underlying proxy shares','Genuine-quote option paper','Forward diagnostics','Private owner-reported actual fills'],
        'safety':{'LIVE_SIGNAL_READY':False,'real_orders':'MANUAL_ONLY','sharing':'Preserved, shown in safe config; no development guest sends','option_performance':'UNAVAILABLE without genuine historical BBO and point-in-time chain','market_session_observed_for_this_release':False},
        'ways_this_could_be_wrong':['Fixture transports cannot prove real provider timing/entitlement or Telegram phone receipt.','A closed-market test cannot prove next-session capture or worker deadline performance.','Historical IEX coverage repaired later does not establish contemporaneous availability.','Day-block intervals need many independent days; all trials/sensitivities count.','Source endpoint response cannot establish complete chains, valid Greeks, liquidity or fills.','Cross-database row counts are successive, not globally atomic.','Windows sleep/offline and uncertain sends can leave monitoring/delivery gaps.']}
    report['latest_completed_session']=latest_session(root,now)
    report['evidence_references']={name:artifact(root,folder/name) for name in ('MARKET_DATA_PROBE.json','SERVICE_OPERATION.json','RESTORE_VERIFICATION.json')}
    ledger=root/'options/reported.sqlite';report['private_ledger_aggregate']=database(ledger) if ledger.exists() else {'state':'ABSENT'}
    if scan(json.dumps(report,default=str)):raise ValueError('COMPLETION_EVIDENCE_SECRET_REJECTED')
    packet['completion']=report
    compact_historical_duplicates(packet,root,command,schedule)
