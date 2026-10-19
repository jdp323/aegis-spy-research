from core.runtime_paths import node_executable
"""Full regression suites run in an isolated source copy, never operational ledgers."""
import sys,os,json,shutil,subprocess,re,time,tempfile
from pathlib import Path
from datetime import datetime,timezone
from core.storage import ROOT
NODE=Path(node_executable())
def run(root=ROOT,output=None):
    root=Path(root);output=Path(output or root/'research/verification');output.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    short_base=Path(os.environ.get('LOCALAPPDATA',tempfile.gettempdir()))/'Temp'/'ag'
    short_base.mkdir(parents=True,exist_ok=True)
    workspace=Path(tempfile.mkdtemp(prefix='s-',dir=short_base))
    test_temp=Path(tempfile.mkdtemp(prefix='t-',dir=short_base))
    ignore={'.venv','.private','runtime','logs','daily_reports','.vendor','__pycache__','.git','demo_sessions','outbox','inbox','users','verification','completion_verification','reports','documentation_archive','schedule_transports','premarket_cache','premarket_authorized_cache','public_cache','closing_cache'}
    for folder,dirs,files in os.walk(root):
        dirs[:]=[d for d in dirs if d not in ignore];relative=Path(folder).relative_to(root);target=workspace/relative;target.mkdir(exist_ok=True,parents=True)
        for name in files:
            p=Path(folder)/name
            if p.suffix in ('.sqlite','.db','.dpapi','.pyc') or name.endswith(('-wal','-shm')) or name in ('access.json','demo_state.json','risk_state.json','system_state.json') or name.startswith(('VERIFICATION_PACKET','account_snapshot','.env')):continue
            shutil.copy2(p,target/name)
    # Installed libraries are read-only inputs. A junction avoids re-copying native packages.
    if (root/'.vendor').is_dir() and os.name=='nt':
        r=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(workspace/'.vendor'),str(root/'.vendor')],capture_output=True)
        if r.returncode:raise RuntimeError('TEST_VENDOR_LINK_FAILED')
    elif (root/'.vendor').is_dir():os.symlink(root/'.vendor',workspace/'.vendor',target_is_directory=True)
    (workspace/'runtime').mkdir();(workspace/'daily_reports').mkdir();(workspace/'test_temp').mkdir()
    runner=workspace/'isolated_suite.py'
    runner.write_text('''import sys,json,unittest,urllib.request,socket
from pathlib import Path
r=Path(__file__).parent;sys.path[:0]=[str(r),str(r/'.vendor')]
original=urllib.request.urlopen
def offline(req,*a,**k):
 from urllib.parse import urlparse
 url=req.full_url if hasattr(req,'full_url') else req
 if urlparse(url).hostname in ('127.0.0.1','localhost','::1'):return original(req,*a,**k)
 raise OSError('HERMETIC_TEST_NETWORK_DISABLED')
urllib.request.urlopen=offline
original_dns=socket.getaddrinfo
def dns(host,*a,**k):
 if host not in ('127.0.0.1','localhost','::1',None):raise OSError('HERMETIC_TEST_NETWORK_DISABLED')
 return original_dns(host,*a,**k)
socket.getaddrinfo=dns
original_host=socket.gethostbyname
def host(name):
 if name not in ('127.0.0.1','localhost','::1'):raise OSError('HERMETIC_TEST_NETWORK_DISABLED')
 return original_host(name)
socket.gethostbyname=host
results={}
for group in ('tests','backtesting','monitoring'):
 suite=unittest.defaultTestLoader.discover(str(r/group),top_level_dir=str(r/group))
 with (r/(group+'.txt')).open('w',encoding='utf-8') as f:result=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
 results[group]={'run':result.testsRun,'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),'failed':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'failed_tests':[str(t) for t,_ in result.failures+result.errors],'skipped_tests':[(str(t),why) for t,why in result.skipped]}
(r/'result.json').write_text(json.dumps(results,indent=2))
''',encoding='utf-8')
    env={k:v for k,v in os.environ.items() if k.upper() in {'PATH','SYSTEMROOT','WINDIR','COMSPEC','PATHEXT','USERPROFILE','LOCALAPPDATA','APPDATA','PROGRAMFILES','PROGRAMFILES(X86)','PROGRAMDATA','NUMBER_OF_PROCESSORS','PROCESSOR_ARCHITECTURE'}}
    env.update(TEMP=str(test_temp),TMP=str(test_temp),PYTHONIOENCODING='utf-8',AEGIS_PYTHON=sys.executable,AEGIS_TELEGRAM_BOT_USERNAME='FixtureResearchBot')
    # Cold Windows imports and packet hashing exceeded five minutes in the
    # pre-open audit. Bound execution without altering any test assertion.
    child=subprocess.run([sys.executable,'-X','utf8',str(runner)],cwd=workspace,env=env,capture_output=True,text=True,encoding='utf-8',timeout=900)
    results=json.loads((workspace/'result.json').read_text()) if (workspace/'result.json').exists() else {'runner':{'failed':1,'errors':1,'reason':'runner failed'}}
    files=sorted(str(p.relative_to(workspace)).replace('\\','/') for p in (workspace/'monitoring').glob('test_*.cjs'))
    # Bound concurrent Windows child-process startup. This is a runner budget,
    # not a wider quote, stream, command or test-assertion tolerance.
    node_command=[str(NODE),'--test','--test-concurrency=1',*files]
    node_timed_out=False
    try:node=subprocess.run(node_command,cwd=workspace,env=env,capture_output=True,text=True,encoding='utf-8',timeout=300)
    except subprocess.TimeoutExpired as error:
        node_timed_out=True
        def decoded(value):return value.decode('utf-8',errors='replace') if isinstance(value,bytes) else value or ''
        node=subprocess.CompletedProcess(node_command,124,decoded(error.stdout),decoded(error.stderr))
    def count(label):
        m=re.search(r'(?:# |ℹ )'+label+r' (\d+)',node.stdout);return int(m[1]) if m else 0
    results['node']={'run':count('tests'),'passed':count('pass'),'failed':count('fail'),'errors':int(node.returncode!=0 and not count('fail')),'skipped':count('skipped'),'files':files,'command':' '.join(node_command),'runner_timeout_seconds':300,'timed_out':node_timed_out}
    results['checked_at']=datetime.now(timezone.utc).isoformat();results['python_command']=str(sys.executable)+' -X utf8 '+str(runner);results['python_discovery']={group:{'start_dir':str(workspace/group),'top_level_dir':str(workspace/group),'pattern':'test*.py'} for group in ('tests','backtesting','monitoring')};results['isolated_workspace']=str(workspace);results['isolated_temp']=str(test_temp);results['temporary_path_policy']='Short separate user-local TEMP roots; retained evidence; assertions unchanged'
    results['successful']=child.returncode==0 and node.returncode==0 and all(x.get('failed',0)==x.get('errors',0)==0 for x in results.values() if isinstance(x,dict))
    from ops.verification_packet import redact
    logs=output/'logs';logs.mkdir(exist_ok=True)
    for name in ('tests','backtesting','monitoring'):
        p=workspace/(name+'.txt')
        if p.exists():(logs/(stamp+'-'+name+'.txt')).write_text(redact(p.read_text(encoding='utf-8')),encoding='utf-8')
    (logs/(stamp+'-node.txt')).write_text(redact(node.stdout+node.stderr),encoding='utf-8')
    (output/'latest_tests.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    return results
if __name__=='__main__':print(json.dumps(run(),indent=2))
