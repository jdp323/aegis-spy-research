from core.runtime_paths import node_executable
"""Read-only inspection and explicit isolated tests. Writes only verification deliverables."""
import json,hashlib,sqlite3,re,os,sys,subprocess,argparse
from pathlib import Path
from datetime import datetime,timezone
from core.storage import ROOT
from core.sessions import ET
CONFIG_KEYS=('symbols','order_execution_enabled','live_signal_enabled','options_risk','options_risk_live_confirmed','allow_unvalidated_paper_trading','signal_expiry_seconds','paper_daily_message_cap','signals','proxy_paper','max_future_skew_seconds','option_data_provider','questrade','price_mismatch_tolerance','buy_limit_buffer','horizons','notifications','min_dte','max_option_spread_pct','require_chain_sanity')
CONFIG_KEYS+=('idea_engine_enabled','trend_lines_silent','idea_daily_cap','idea_cooldown_minutes','cooloff_minutes','cooloff_losses','min_rr','early_session_ideas','rough_risk_delta_range','premium_cap_mode','report_time','recap_time','idea_runaway_limit','idea_stop_atr_fraction','setup_enabled','negative_setup_overrides')
SECRET_PATTERNS=(r'\b\d{6,}:[A-Za-z0-9_-]{25,}\b',r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'(?i)(?:access_token|refresh_token|api_secret|APCA_API_SECRET_KEY|password)\s*[=:]\s*["\']?[A-Za-z0-9_~-]{12,}',r'\bAKIA[A-Z0-9]{16}\b')
def scan(text):return [str(i) for i,p in enumerate(SECRET_PATTERNS) if re.search(p,text)]
def redact(text):
    for p in SECRET_PATTERNS:text=re.sub(p,'[REDACTED]',text)
    if '@' in text:text=re.sub(r'[\w.+-]{1,64}@[\w.-]{1,253}\.[A-Za-z]{2,63}','[REDACTED_EMAIL]',text)
    text=re.sub(r'(?i)(chat_id|user_id|telegram_id|username|email)["\']?\s*[:=]\s*["\']?[^\s,}\n]+',r'\1: [REDACTED]',text)
    text=re.sub(r'(?i)(?:reply-)?telegram-\d+', 'telegram-[REDACTED_ID]',text)
    text=re.sub(r'monitoring[/\\]users[/\\][a-f0-9]{24}', 'monitoring/users/[REDACTED_ACCESS]',text)
    # Numeric destinations in Node assertion output are not source evidence.
    text=re.sub(r'(?i)(AEGIS_LOCAL_SETUP_TOKEN[^\n]{0,150})','[REDACTED_LOCAL_CAPABILITY]',text)
    return text
def redact_deep(value):
    if isinstance(value,dict):return {k:('[REDACTED]' if k.lower() in ('chat_id','user_id','telegram_id','username','email') else redact_deep(v)) for k,v in value.items()}
    if isinstance(value,list):return [redact_deep(x) for x in value]
    if isinstance(value,tuple):return [redact_deep(x) for x in value]
    return redact(value) if isinstance(value,str) else value
def safe_config(config):
    d={k:config[k] for k in CONFIG_KEYS if k in config}
    if 'signals' in d:d['signals']={'shared':d['signals'].get('shared',False)}
    d['heartbeat_configured']=bool(config.get('heartbeat_url'))
    return d
def read_json(path,default=None):
    try:return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError,ValueError):return default
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def ro(path):
    db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True);db.execute('PRAGMA query_only=ON');return db
def database(path):
    if not Path(path).exists():return {'state':'ABSENT'}
    db=ro(path)
    try:
        names=[x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")];tables={};contamination={}
        for table in names:
            if not re.fullmatch('[A-Za-z_]+',table):continue
            tables[table]=db.execute('SELECT count(*) FROM '+table).fetchone()[0]
            cols=[r[1] for r in db.execute('PRAGMA table_info('+table+')')]
            if 'payload' in cols:
                count=0
                for row in db.execute('SELECT payload FROM '+table):
                    try:
                        from core.isolation import assert_real
                        assert_real(json.loads(row[0]))
                    except ValueError:count+=1
                contamination[table]=count
        return {'state':'READ_ONLY_WAL_AWARE_SNAPSHOT','user_version':db.execute('PRAGMA user_version').fetchone()[0],'tables':tables,'simulated_rows_by_table':contamination,'limitation':'mode=ro/query_only includes committed WAL. Counts across different databases are successive observations, not one cross-database transaction.'}
    finally:db.close()
def state(root):
    p=Path(root)/'runtime/aegis.sqlite'
    if not p.exists():return {}
    db=ro(p)
    try:return {k:json.loads(v) for k,v in db.execute('SELECT key,payload FROM state') if k in ('quote:SPY','research_quote:SPY:iex','risk','selection','ntp_clock','questrade_health','worker_health','stream:iex','stream:sip','stream:opra','stream_clock:iex','stream_clock:sip','stream_bars:SPY','research_stream_bars:SPY:iex','chain','live_verify_deployment','recorder_health')}
    finally:db.close()
def manifest(root,backup):
    root=Path(root);backup=Path(backup) if backup else None;rows=[]
    for folder,dirs,files in os.walk(root):
        dirs[:]=[d for d in dirs if d not in ('.git','.vendor','__pycache__','verification','completion_verification','workspaces','command_workspaces','logs','runtime','outbox','inbox','users','documentation_archive','reports','premarket_cache','premarket_authorized_cache','public_cache','closing_cache')]
        for name in files:
            p=Path(folder)/name
            if p.suffix=='.pyc' or name.endswith(('-wal','-shm','.lock','.pending')):continue
            relative=p.relative_to(root);old=backup/relative if backup else None
            h=sha(p)
            if old is None or not old.is_file() or sha(old)!=h:rows.append({'path':relative.as_posix(),'state':'MODIFIED' if old and old.is_file() else 'NEW','sha256':h,'bytes':p.stat().st_size})
    return rows
def requirements(root):
    spec=read_json(Path(root)/'research/v5_requirements.json',None)
    if spec is None:spec=read_json(Path(root)/'research/combined_requirements.json',[]) or []
    for row in spec:
        row=dict(row);files=row.get('files',[]);present=bool(files) and all((Path(root)/f).exists() for f in files)
        row['status']=row.pop('status_override',None) or ('IMPLEMENTED' if present else 'NOT DONE');row['evidence']=row.pop('evidence_override',None) or ('Source exists; named fixtures do not establish full external operation.' if present else row.get('gap','No complete implementation evidence.'))
        row.pop('gap',None)
        row['test_names']=row.get('test_names',[])[:3]
        yield row
def generated_samples():
    from ops.demo import fixture
    from core.verdict import short
    from monitoring.paper_alerts import signal_text
    from options.trade_plan import exit_conditions
    f=fixture();s=f['signal'];now=f['now'];guideline=dict(s,option_contract=None,option_plan=None,feed_quality='IEX')
    put=fixture('put')['signal'];n=dict(s,paper_eligible=False,paper_blockers=['NEWS_UNAVAILABLE_OR_BLACKOUT'])
    return {'call_guideline_EXAMPLE':short(guideline,now,simulation=True),'put_specific_EXAMPLE_SIMULATED':short(put,now,simulation=True),'no_trade_EXAMPLE':short(n,now,simulation=True),'closed_EXAMPLE':short(n,now.replace(hour=23),simulation=True),'paper_EXAMPLE':signal_text(guideline,now),'exit_EXAMPLE':'EXIT REVIEW — SPY '+f"{s['t1']:.2f}"+' / option bid UNAVAILABLE (simulated option quote is rejected by the real exit helper).\n'+exit_conditions(s['option_plan'],s,{},s['option_contract']['quote'],now)['text']}
def collect(root=ROOT,run_tests=False,live=False):
    root=Path(root);out=root/'research/verification';out.mkdir(parents=True,exist_ok=True);now=datetime.now(timezone.utc);config=read_json(root/'config/upgrade.json',{}) or {};backup=read_json(root/'research/v6_backup.json',None) or read_json(root/'research/v5_backup.json',None) or read_json(root/'research/combined_backup.json',{}) or {};s=state(root)
    from news.engine import NewsProvider
    news=NewsProvider(root/'config/news_calendar.json').snapshot(now)
    from core.readiness import evaluate
    from research.live_trend import evaluate as live_trend
    class ReadOnlyState:
        def get(self,key,default=None):return s.get(key,default)
    readiness=evaluate({'underlying':s.get('quote:SPY'),'live_trend':live_trend(ReadOnlyState(),now),'data_availability':{'options':(s.get('chain') or {}).get('quality','UNAVAILABLE')},'risk':s.get('risk'),'selection':s.get('selection'),'news':news},config)
    gates=readiness['gates']
    tests=read_json(out/'latest_tests.json',{})
    if run_tests:
        from ops.test_runner import run
        tests=run(root,out)
    node=Path(node_executable());version=subprocess.run([str(node),'--version'],capture_output=True,text=True).stdout.strip() if node.exists() else 'UNAVAILABLE'
    registry=(root/'monitoring/command_registry.cjs').read_text();commands=re.findall(r"^\s*\['([a-z_]+)','([^']*)','([^']*)'\]",registry,re.M);menus=re.search(r'const main=\[([^\]]+)\]',registry)
    providers={}
    forbidden=r'/(?:accounts|balances|positions|orders|executions|activities)(?:/|[\'"?])'
    for name in ('data/providers.py','data/questrade.py','data/research_inputs.py'):
        p=root/name;providers[name]={'forbidden_endpoint_matches':len(re.findall(forbidden,p.read_text())) if p.exists() else None,'sha256':sha(p) if p.exists() else None,'proof':'Static literal endpoint scan only; runtime allowlists and tests are stronger evidence.'}
    notifier=(root/'monitoring/notifier.cjs').read_text()
    packet={'header':{'tag':'VERIFIED','utc':now.isoformat(),'et':now.astimezone(ET).isoformat(),'repository':str(root),'prompt':'combined V3+V4','backup':backup.get('backup'),'python':sys.version.split()[0],'node':version,'git_commit':'UNAVAILABLE (not assumed)'},'change_manifest':manifest(root,backup.get('backup')),'config_VERIFIED':safe_config(config),'requirements':list(requirements(root)),'tests':tests,'test_claim': 'TESTED only for named passing tests, not every feature or external dependency. Latest stored run.' if not run_tests else 'Current isolated full run; no operational ledgers or Telegram transports used.','commands':commands,'main_menu_VERIFIED':re.findall(r"'([^']+)'",menus[1]) if menus else [],'gates_before':backup.get('gates_before'),'gates_after_observed':gates,'safety':{'order_execution_enabled':config.get('order_execution_enabled'),'live_signal_enabled':config.get('live_signal_enabled'),'LIVE_SIGNAL_READY':False,'blocked_kinds_static':all(k in notifier for k in ('INFO','RESEARCH','INTERVENTION','TEST')) and "if(!['INFO','RESEARCH','INTERVENTION','TEST'].includes(event.kind))" in notifier,'providers':providers,'real_databases':{str(p.relative_to(root)):database(p) for p in (root/'runtime/aegis.sqlite',root/'runtime/paper.sqlite',root/'runtime/history.sqlite')},'guest_routing':'Owner-only paper/exit alerts; demo replies only to authenticated requester. See fake-transport and callback tests.','storage_queries':'SELECT count(*) FROM each table; recursively assert_real(json.loads(payload)); immutable=1, mode=ro. No row contents included.'},'status':{'calendar':{k:news.get(k) for k in ('quality','risk','verified_at','coverage_through','coverage_complete','stale','date_only_event_count','source_status')},'calendar_categories':{k:sum(e['type']==k for e in news.get('events',[])) for k in sorted({e['type'] for e in news.get('events',[])})},'clock':s.get('ntp_clock'),'skew_budget':config.get('max_future_skew_seconds'),'questrade':s.get('questrade_health') or {'status':'QUESTRADE_NOT_CONFIGURED_OR_NO_STORED_HEALTH'},'stream_health':{k:s.get(k) for k in ('stream:iex','stream:sip','stream:opra')}},'samples_EXAMPLE':generated_samples(),'demo':{},'gaps':{},'weak_points':['Questrade schema lacks a verified bid/ask source timestamp.','Refresh consumption and local persistence cannot form one remote transaction.','Cross-process refresh concurrency requires stress testing.','Greek units and IV conventions need provider evidence.','Local Taylor estimates omit IV/skew changes.','Synthetic demo paths do not validate a market strategy.','Proxy evidence is single-exchange shares, not option P&L.','BLS direct requests and ICS can return HTTP 403.','Static scans do not establish absence of all dynamic behavior.','Computer sleep/offline intervals can miss exit conditions.']}
    for name in ('DECISIONS.md','OWNER_ACTIONS.md','KNOWN_ISSUES.md','UPGRADE_PROGRESS.md'):
        p=root/'research'/name;packet['gaps'][name]={'excerpt':redact(p.read_text(encoding='utf-8')[-3000:]),'sha256':sha(p),'scope':'Latest 3000 characters; full documents are listed by hash; explicit current gaps retained.'} if p.exists() else 'NOT DONE'
    transcript=sorted((root/'daily_reports').glob('DEMO_TRANSCRIPT_*.md'))
    if transcript:packet['demo']={'path':str(transcript[-1].relative_to(root)),'sha256':sha(transcript[-1]),'first_60_lines':'\n'.join(transcript[-1].read_text(encoding='utf-8').splitlines()[:60]),'tag':'EXAMPLE — SIMULATED, NOT PROFIT EVIDENCE'}
    if live:
        from data.questrade import QuestradeProvider
        from data.questrade_check import check
        packet['live_readonly']=check(QuestradeProvider(readonly=True))
    packet['readiness_reasons']=readiness['blockers']
    packet['command_visibility']={'owner_only':['users','invite','revoke','alerts'],'guest_menu':packet['main_menu_VERIFIED'],'all_other_typed_commands':'Retained; private ledgers scoped to authenticated sender; /paper owner-only unless explicit sharing.'}
    packet['verification_logs']=[{'name':p.name,'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted((out/'logs').glob('*.txt'))[-8:]]
    packet['migration_notes']={'signal_schema':3,'scoring':'evidence-rubric-v3','selection':'research-ranking-v2','option_baseline':'events.kind=paper_baseline; excluded from paper risk/statistics','premium_accuracy':'premium_estimates additive table with no-update/no-delete triggers','old_records':'Legacy fields default to UNAVAILABLE; no historical rewrites.'}
    packet['live_status_readonly']={'recorder':s.get('recorder_health'),'live_verify':s.get('live_verify_deployment')}
    smoke=read_json(root/'research/SERVICE_SMOKE_CHECK.json',{}) or {}
    telegram=read_json(root/'research/TELEGRAM_OWNER_SMOKE.json',{}) or {}
    task=read_json(root/'research/AUTOSTART_CHECK.json',{}) or {}
    packet['deployment_observations']={'observed_at':smoke.get('observed_at'),'service_states':{k:v.get('state') for k,v in smoke.get('services',{}).get('components',{}).items()},'dashboard_http':smoke.get('dashboard',{}).get('http'),'owner_TEST_receipt':telegram.get('receipt',{}).get('status'),'phone_receipt_confirmed':telegram.get('phone_receipt_confirmed',False),'resent':telegram.get('resend_performed',False),'autostart_installed':task.get('installed',False),'current_user_only':task.get('current_user_only',False),'autostart_launches_start_aegis':task.get('launches_start_aegis',False),'scope':'Saved smoke observations, not continuous health or phone-delivery proof.'}
    p=root/'runtime/aegis.sqlite';values=[]
    if p.exists():
        db=ro(p)
        try:values=[json.loads(row[0])['premium_usd'] for row in db.execute("SELECT payload FROM events WHERE kind='premium_cap_rejection'")]
        finally:db.close()
    import statistics
    packet['premium_cap_analysis']={'state':'MEASURED' if values else 'INSUFFICIENT_DATA','verified_quote_rejection_samples':len(values),'mean_rejected_premium_usd':statistics.mean(values) if values else None,'median_rejected_premium_usd':statistics.median(values) if values else None,'cap_usd':config.get('options_risk',{}).get('max_trade_premium_usd'),'note':'Distinct fresh verified quote rejections only; no option sample was invented.'}
    if (root/'research/v5_backup.json').exists():
        from ops.v5_verification import extend
        extend(packet,root,now)
    if (root/'research/v6_backup.json').exists():
        from ops.v6_verification import extend as v6_extend
        v6_extend(packet,root,now)
    if (root/'research/completion_backup.json').exists():
        from ops.completion_verification import extend as completion_extend
        completion_extend(packet,root,now)
    try:
        result=subprocess.run(['git','rev-parse','HEAD'],cwd=root,capture_output=True,text=True,timeout=5)
        if result.returncode==0 and re.fullmatch('[a-f0-9]{40}',result.stdout.strip()):packet['header']['git_commit']=result.stdout.strip()
    except (OSError,subprocess.TimeoutExpired):pass
    return packet
def write(packet,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True);stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');base=output/('VERIFICATION_PACKET_'+stamp)
    raw=json.dumps(packet,ensure_ascii=False,indent=2,allow_nan=False)
    # Bound untrusted input before regex scans. Oversized artifacts are refused,
    # not subjected to quadratic work in the redaction path.
    if len(raw.encode('utf-8'))>150000:raise ValueError('PACKET_TOO_LARGE')
    # Reject before redaction: a raw secret accidentally placed in a field must not be masked into approval.
    if scan(raw):raise ValueError('PACKET_REFUSED_SECRET_PATTERN: matching pattern identifiers '+','.join(scan(raw)))
    raw=json.dumps(redact_deep(packet),ensure_ascii=False,indent=2,allow_nan=False);md='# AEGIS independent-review packet\n\nTags: VERIFIED = dated inspection; TESTED = named passing test only; IMPLEMENTED = source exists; NOT DONE = missing evidence.\n\nThis release does not validate a strategy or enable live signals. Assumption-based premium targets are not verified option performance. Repeated detail is summarized; referenced full evidence is retained with its original as-of time, path and hash. A hash verifies artifact bytes, not a market or delivery claim.\n\n```json\n'+raw+'\n```\n'
    if scan(md):raise ValueError('PACKET_REFUSED_SECRET_PATTERN')
    if len(md.encode('utf-8'))>150000:raise ValueError('PACKET_TOO_LARGE')
    base.with_suffix('.json').write_text(raw,encoding='utf-8');base.with_suffix('.md').write_text(md,encoding='utf-8');return base.with_suffix('.md')
def main():
    a=argparse.ArgumentParser();a.add_argument('--run-tests',action='store_true');a.add_argument('--live',action='store_true');args=a.parse_args()
    try:
        packet=collect(run_tests=args.run_tests,live=args.live)
        print(write(packet,ROOT/'research/verification'))
        if args.run_tests and not packet.get('tests',{}).get('successful'):raise SystemExit(1)
    except ValueError as e:print(str(e));raise SystemExit(1)
if __name__=='__main__':main()
