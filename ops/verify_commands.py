from core.runtime_paths import node_executable
"""Registry verification using actual Node/Python handlers in an isolated source copy."""
import os,json,shutil,subprocess,sys,tempfile
from pathlib import Path
from datetime import datetime,timezone
from core.storage import ROOT
def verify(root=ROOT):
    root=Path(root);now=datetime.now(timezone.utc);stamp=now.strftime('%Y%m%dT%H%M%S%fZ')
    short=Path(os.environ.get('LOCALAPPDATA',tempfile.gettempdir()))/'Temp'/'ag';short.mkdir(parents=True,exist_ok=True)
    workspace=Path(tempfile.mkdtemp(prefix='c-',dir=short));isolated_temp=Path(tempfile.mkdtemp(prefix='t-',dir=short))
    ignore={'.venv','.private','runtime','logs','daily_reports','.vendor','__pycache__','.git','demo_sessions','outbox','inbox','users','verification','completion_verification','reports','documentation_archive','command_workspaces','schedule_transports','premarket_cache','premarket_authorized_cache','public_cache','closing_cache'}
    for folder,dirs,files in os.walk(root):
        dirs[:]=[x for x in dirs if x not in ignore];target=workspace/Path(folder).relative_to(root);target.mkdir(parents=True,exist_ok=True)
        for name in files:
            p=Path(folder)/name
            if p.suffix in ('.sqlite','.db','.dpapi','.pyc') or name in ('access.json','demo_state.json','risk_state.json','system_state.json') or name.startswith(('account_snapshot','.env')) or name.endswith(('-wal','-shm')):continue
            shutil.copy2(p,target/name)
    # Disable every remote Python request from the command children, before imports.
    (workspace/'sitecustomize.py').write_text("import socket,urllib.request\ndef blocked(*a,**k):raise OSError('FIXTURE_NETWORK_DISABLED')\nsocket.getaddrinfo=blocked\nurllib.request.urlopen=blocked\n",encoding='utf-8')
    (workspace/'runtime').mkdir();(workspace/'daily_reports').mkdir();(workspace/'test_temp').mkdir()
    node=Path(node_executable())
    env={k:v for k,v in os.environ.items() if k.upper() in {'PATH','SYSTEMROOT','WINDIR','COMSPEC','PATHEXT','USERPROFILE','LOCALAPPDATA','APPDATA','PROGRAMFILES','PROGRAMFILES(X86)','PROGRAMDATA','NUMBER_OF_PROCESSORS','PROCESSOR_ARCHITECTURE'}}
    env.update(TEMP=str(isolated_temp),TMP=str(isolated_temp),PYTHONIOENCODING='utf-8',PYTHONPATH=str(workspace),AEGIS_PYTHON=sys.executable,AEGIS_TELEGRAM_BOT_USERNAME='FixtureResearchBot')
    # Actual fills are seeded into isolated owner/guest ledgers only.
    import importlib.util
    spec=importlib.util.spec_from_file_location('fixture_ledger',workspace/'options/ledger.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    for folder in (workspace/'options',workspace/'monitoring/users'/__import__('hashlib').sha256(b'telegram:1002').hexdigest()[:24]):
        folder.mkdir(parents=True,exist_ok=True);ledger=module.Ledger(folder/'reported.sqlite')
        try:ledger.record('fixture-seed','BUY','SPY261014C00500000',10,'2.40','.65','2026-10-08T09:45:00-04:00')
        finally:ledger.close()
    #315 isolated handler processes can exceed three minutes on a cold PC.
    r=subprocess.run([str(node),'ops/command_harness.cjs'],cwd=workspace,env=env,capture_output=True,text=True,encoding='utf-8',timeout=900)
    try:data=json.loads(r.stdout)
    except ValueError:data={'rows':[],'harness_error':r.stderr[-1500:],'menu':[],'command_count':0}
    data.update(at=now.isoformat(),status='PASS' if r.returncode==0 and data['rows'] else 'FAIL',command=str(node)+' ops/command_harness.cjs',isolation='Source copy, fake transports, network blocked; original ledgers untouched.',limitations='Reply/routing/role/argument safety tested. External feeds and phone receipt not established. Callback authentication/idempotency exercised by full Node/Python suites, not every command invocation.')
    base=root/'research'/('COMMAND_VERIFICATION_'+stamp);base.with_suffix('.json').write_text(json.dumps(data,indent=2),encoding='utf-8');lines=['# Command verification',data['status'],'','| Command | Role | Arguments | Result | EXAMPLE excerpt |','|---|---|---|---|---|']
    for row in data['rows']:lines.append('| /'+row['command']+' | '+row['role']+' | '+row['arguments']+' | '+row['result']+' | '+row['reply_excerpt'].replace('\n','; ').replace('|','/').replace('<','&lt;')+' |')
    if data.get('harness_error'):lines+=['Harness failure: '+data['harness_error']]
    base.with_suffix('.md').write_text('\n'.join(lines),encoding='utf-8')
    registry=(root/'monitoring/command_registry.cjs').read_text(encoding='utf-8');import re
    commands=re.findall(r"^\s*\['([a-z_]+)','([^']*)','([^']*)'\]",registry,re.M)
    docs=['# Commands — generated from registry and fixture verification','','Main menu: /trend /score /demo /news /more /help','',data['isolation'],'','| Command | Arguments | Purpose | Fixture result |','|---|---|---|---|']
    for name,args,description in commands:
        results=[x['result'] for x in data['rows'] if x['command']==name]
        docs.append('| /'+name+' | '+args+' | '+description+' | '+('PASS' if results and all(x=='PASS' for x in results) else 'FAIL / NOT VERIFIED')+' |')
    docs+=['','Owner-only: users, invite, revoke, alerts. Invited members retain private fill/position reports. Stranger replies require an invitation; join accepts a genuine one-use invitation. Paper/score permissions follow existing owner-sharing rules.','',
           'V5 alert syntax: `/alerts trend_lines on|off`, `/alerts ideas on|off`, `/alerts silent on|off`, `/alerts setup SETUP_NAME on|off`. Enabling a setup explicitly overrides NEGATIVE alert suppression; it never enables live signals.','',
           'Demo scenes: `/demo start`, call, put, swing, no-trade, next, chart, bought, quantity, premium, fees, time, confirm, sold, skipped, status, stop, v5. All are simulated; none writes a real fill.','',
           '## Generated fixture message examples — not live market data','The full timestamped command verification report contains all three roles and argument variants. Below are actual valid-argument fixture replies, abbreviated. Unavailable external data is an honest fixture outcome.']
    for name,_,_ in commands:
        row=next((x for x in data['rows'] if x['command']==name and x['role']=='owner' and x['arguments']=='valid'),None)
        if row:docs+=['','### /'+name,'```text',row['reply_excerpt'],'```']
    (root/'COMMANDS.md').write_text('\n'.join(docs),encoding='utf-8');return base.with_suffix('.md'),data
if __name__=='__main__':
    p,d=verify();print(p);raise SystemExit(d['status']!='PASS')
