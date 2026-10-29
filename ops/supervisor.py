"""Detached local service group; bounded restart backoff and local singleton socket."""
import json,os,subprocess,sys,socket,time,signal,argparse
from pathlib import Path
from core.storage import ROOT,iso
from datetime import datetime,timezone
from data.reliability import Events,PauseProbe,active,watchdog_age
from data.models import stamp,finite
import sqlite3
def child_python(executable=sys.executable,windows=os.name=='nt'):
    # pythonw hosts the invisible supervisor, but children need normal stdio
    # for durable logs and existing JSON/CLI transports. CREATE_NO_WINDOW below
    # keeps those console-runtime children invisible.
    return str(Path(executable).with_name('python.exe')) if windows and Path(executable).name.lower()=='pythonw.exe' else executable
PY=child_python()
from core.runtime_paths import node_executable
NODE=node_executable()
COMMANDS={'dashboard':[PY,'app.py','serve','--port','8767'],'research':[PY,'-m','core.spy_research','--loop'],'worker':[PY,'-m','core.upgrade_service'],'stream':[PY,'-m','data.stream'],'telegram':[NODE,'monitoring/commands.cjs'],'dispatcher':[NODE,'monitoring/dispatch.cjs']}
COMMANDS['shadow']=[PY,'-m','ops.shadow_worker']

def runtime_environment():
    env=dict(os.environ);env.setdefault('AEGIS_PYTHON',PY);env.setdefault('AEGIS_NODE',NODE)
    return env
def publish_status(states,root=ROOT,sleep=time.sleep):
    """A briefly locked telemetry file must not stop the supervised services."""
    tmp=root/'runtime/services.tmp';target=root/'runtime/services.json'
    for delay in (.05,.1,.2):
        try:
            tmp.write_text(json.dumps({'pid':os.getpid(),'at':iso(),'components':states}),encoding='utf-8');tmp.replace(target);return True
        except OSError:sleep(delay)
    return False
def alive(pid):
    if os.name=='nt':
        import ctypes
        h=ctypes.windll.kernel32.OpenProcess(0x1000,False,int(pid))
        if h:ctypes.windll.kernel32.CloseHandle(h);return True
        return False
    try:os.kill(pid,0);return True
    except ProcessLookupError:return False
def clean_stale():
    for f in (ROOT/'monitoring/inbox/listener.lock',ROOT/'monitoring/research_worker.lock'):
        if f.exists():
            pid=json.loads(f.read_text())['pid']
            if alive(pid):raise RuntimeError('Existing component running; stop its existing launcher before takeover')
            f.unlink()
STREAM_CONTROL_POLICY='stream-control-progress-v1'

def stream_control_progress(health,now,started):
    """Bounded process-control progress; never market-data freshness."""
    try:
        began=stamp(health['connection_started_at']);reported=stamp(health['at'])
        if not started<=began<=reported<=now:return False
        age=(now-began).total_seconds();state=health.get('state')
        # Existing socket bounds: open15 + greeting10 + auth10 + close5.
        if state=='CONNECTING':return age<40
        # A control heartbeat cannot extend the existing90s market wait.
        if state in ('CONNECTED','CONNECTED_IDLE'):return age<90
        if state=='FEED_DISCONNECTED' and health.get('error_type')=='PermissionError':
            delay=health.get('next_retry_seconds')
            # Existing bounded retry+jitter, plus5s for the retry handoff.
            return finite(delay) and 0<=delay<=301 and (now-reported).total_seconds()<delay+5
    except (KeyError,TypeError,ValueError):pass
    return False

def stream_restart_due(root,now,started):
    if not active(now) or started is None or (now-started).total_seconds()<300:return False
    try:
        db=sqlite3.connect((root/'runtime/aegis.sqlite').as_uri()+'?mode=ro',uri=True,timeout=.5)
        try:
            db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
            def get(key):
                row=db.execute('SELECT payload FROM state WHERE key=?',(key,)).fetchone();return json.loads(row[0]) if row else {}
            health=get('stream:iex')
            if health.get('state') in ('FEED_NOT_CONFIGURED','IDLE_NO_CONTRACT_SUBSCRIPTIONS'):return False
            if stream_control_progress(health,now,started):return False
            return watchdog_age(get('last_market:iex'),now,started)>=300
        finally:db.close()
    except (OSError,sqlite3.Error,ValueError):return False
def clear_previous_shutdown(root=ROOT):
    # Called only after exclusive ownership of the supervisor socket. Do not
    # consume a stop request: it may represent a new owner instruction.
    (root/'runtime/shutdown.request').unlink(missing_ok=True)
def run():
    sock=socket.socket();sock.bind(('127.0.0.1',8768));sock.listen();sock.setblocking(False);clean_stale();stop=False;children={};attempts={};due={};started={};status_failed=False
    clear_previous_shutdown()
    def shutdown(*args):nonlocal stop;stop=True
    signal.signal(signal.SIGINT,shutdown);signal.signal(signal.SIGTERM,shutdown)
    logs=ROOT/'logs/services';logs.mkdir(parents=True,exist_ok=True);(ROOT/'runtime').mkdir(exist_ok=True)
    events=Events(ROOT/'runtime/observability.sqlite');probe=PauseProbe();stream_started=None
    try:
        while not stop:
            now=datetime.now(timezone.utc);pause=probe.check(now)
            if pause:events.add('PROCESS_PAUSED','supervisor',now,**pause)
            child=children.get('stream')
            if child and child.poll() is None and stream_restart_due(ROOT,now,stream_started):
                events.add('WATCHDOG_RESTART','supervisor',now,reason='NO_VALID_MARKET_MESSAGE_300_SECONDS');child.terminate();stream_started=now
            try:client,_=sock.accept();client.close()
            except BlockingIOError:pass
            if (ROOT/'runtime/stop.request').exists():(ROOT/'runtime/stop.request').unlink();break
            states={}
            for name,cmd in COMMANDS.items():
                child=children.get(name)
                if child and child.poll() is not None:
                    attempts[name]=attempts.get(name,0)+1;due[name]=time.monotonic()+min(300,2**min(attempts[name],8));children.pop(name);child=None
                    if name in ('telegram','research'):
                        f=ROOT/('monitoring/inbox/listener.lock' if name=='telegram' else 'monitoring/research_worker.lock')
                        if f.exists() and not alive(json.loads(f.read_text())['pid']):f.unlink()
                if not child and time.monotonic()>=due.get(name,0):
                    env=runtime_environment()
                    if name=='shadow':
                        from ops.shadow_worker import environment
                        env=environment()
                    if name in ('worker','stream'):
                        from data.credentials import child_environment
                        try:env=child_environment(env)
                        except RuntimeError:
                            due[name]=time.monotonic()+60
                            states[name]={'pid':None,'state':'MARKET_DATA_CONFIG_UNREADABLE','restarts':attempts.get(name,0)}
                            continue
                    with (logs/(name+'.log')).open('ab') as log:child=subprocess.Popen(cmd,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=log,env=env,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                    children[name]=child;started[name]=time.monotonic()
                    if name=='stream':stream_started=now
                if child and time.monotonic()-started[name]>300:attempts[name]=0
                states[name]={'pid':child.pid if child else None,'state':'RUNNING' if child else 'RESTART_BACKOFF','restarts':attempts.get(name,0)}
            published=publish_status(states)
            if not published and not status_failed:print('STATUS_PUBLICATION_DEFERRED: services remain running; status heartbeat may become stale.',flush=True)
            if published and status_failed:print('STATUS_PUBLICATION_RECOVERED',flush=True)
            status_failed=not published;time.sleep(1)
    finally:
        (ROOT/'runtime/shutdown.request').touch()
        deadline=time.monotonic()+25
        while any(p.poll() is None for name,p in children.items() if name!='dashboard') and time.monotonic()<deadline:time.sleep(.25)
        for p in children.values():
            if p.poll() is None:p.terminate()
        for p in children.values():
            try:p.wait(timeout=10)
            except subprocess.TimeoutExpired:p.kill()
        events.close();sock.close()
def start():
    s=socket.socket();running=s.connect_ex(('127.0.0.1',8768))==0;s.close()
    if running:print('AEGIS supervisor already running');return
    clean_stale();logs=ROOT/'logs/services';logs.mkdir(parents=True,exist_ok=True)
    (ROOT/'runtime').mkdir(exist_ok=True);(ROOT/'runtime/stop.request').unlink(missing_ok=True);(ROOT/'runtime/shutdown.request').unlink(missing_ok=True)
    flags=(subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_NO_WINDOW) if os.name=='nt' else 0
    with (logs/'supervisor.log').open('ab') as log:p=subprocess.Popen([PY,'-m','ops.supervisor','run'],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=flags,start_new_session=os.name!='nt')
    print('Supervisor launched; PID',p.pid,'Check runtime/services.json and logs/services.')
def status(root=ROOT,clock=None,probe=True):
    """Read-only service/heartbeat observation; never starts a Store or service."""
    def read(name):
        try:return json.loads((Path(root)/name).read_text(encoding='utf-8'))
        except (OSError,ValueError):return {}
    value=read('runtime/services.json');components={}
    for name,r in value.get('components',{}).items():
        components[name]={'state':r.get('state','UNAVAILABLE'),'process_alive':alive(r['pid']) if r.get('pid') else False,'restarts':r.get('restarts',0)}
    hearts={}
    from data.models import stamp
    for name,path in (('supervisor','runtime/services.json'),('listener','runtime/telegram_health.json'),('dispatcher','runtime/dispatcher_health.json')):
        r=value if name=='supervisor' else read(path)
        hearts[name]={'at':r.get('at'),'age_seconds':None,'state':r.get('state','UNAVAILABLE')}
    # This JSON progress path is independent of a blocked market database. A
    # phase-start timestamp is not represented as completed useful work.
    progress=read('runtime/worker_progress.json');worker={}
    for key in ('phase','state','at','phase_started_at','started_at','last_completed_at','duration_seconds','budget_seconds','deadline_missed','error_type','sqlite_errorcode','sqlite_errorname'):
        if key in progress:worker[key]=progress[key]
    worker.update(completed_work_age_seconds=None,active_phase_age_seconds=None)
    path=Path(root)/'runtime/aegis.sqlite'
    if path.is_file():
        try:
            db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=.5)
            try:
                row=db.execute("SELECT payload FROM state WHERE key='worker_health'").fetchone()
                health=json.loads(row[0]) if row else {}
            finally:db.close()
            worker['cycle']={key:health[key] for key in ('state','at','cycle_seconds','cycle_budget_seconds','cycle_deadline_missed','error_type','sqlite_errorcode','sqlite_errorname','database') if key in health}
        except (OSError,sqlite3.Error,ValueError):worker['database_read']='UNAVAILABLE'
    hearts['worker']=worker or {'state':'UNAVAILABLE'}
    http='NOT_PROBED'
    if probe:
        import urllib.request
        try:
            with urllib.request.urlopen('http://127.0.0.1:8767/healthz',timeout=2) as response:http=response.status;response.read(4096)
        except (OSError,TimeoutError):http='UNAVAILABLE'
    # Sample the evaluation clock after every file/database read and bounded
    # HTTP probe. Concurrent writers may publish newer timestamps during reads;
    # taking it earlier would manufacture negative ages. Real future times stay
    # signed: this diagnostic neither clamps ages nor changes freshness gates.
    now=(clock or (lambda:datetime.now(timezone.utc)))()
    for name in ('supervisor','listener','dispatcher'):
        try:hearts[name]['age_seconds']=round((now-stamp(hearts[name]['at'])).total_seconds(),3)
        except (KeyError,ValueError,TypeError):pass
    age=hearts['supervisor']['age_seconds']
    if age is None or not 0<=age<=30:
        for component in components.values():
            component['reported_state']=component['state'];component['state']='STALE_STATUS_RECORD'
    for component in components.values():component['pid_check_scope']='PID existence only; current heartbeat/progress and HTTP required. PID reuse is possible.'
    for field,label in (('last_completed_at','completed_work_age_seconds'),('phase_started_at','active_phase_age_seconds')):
        try:worker[label]=round((now-stamp(progress[field])).total_seconds(),3)
        except (KeyError,ValueError,TypeError):worker[label]=None
    if 'cycle' in worker:
        try:worker['cycle']['age_seconds']=round((now-stamp(worker['cycle']['at'])).total_seconds(),3)
        except (KeyError,ValueError,TypeError):worker['cycle']['age_seconds']=None
    return {'at':now.isoformat(),'read_only':True,'components':components,'heartbeats':hearts,'dashboard_http':http,'LIVE_SIGNAL_READY':False,'order_execution_enabled':False,'limitation':'Process existence and local HTTP do not establish live market readiness.'}
def main(argv=None):
    parser=argparse.ArgumentParser(description='AEGIS research services; no trading execution. Default is read-only status.')
    parser.add_argument('mode',nargs='?',default='status',choices=('start','run','stop','status'))
    mode=parser.parse_args(argv).mode
    if mode=='status':print(json.dumps(status(),indent=2));return
    if mode=='run':run()
    elif mode=='stop':
        (ROOT/'runtime').mkdir(exist_ok=True);(ROOT/'runtime/stop.request').touch();print('Stop requested',flush=True)
        for _ in range(200):
            sock=socket.socket();running=sock.connect_ex(('127.0.0.1',8768))==0;sock.close()
            if not running:print('Supervisor stopped');break
            time.sleep(.2)
        else:raise RuntimeError('Stop timeout; inspect service logs')
    elif mode=='start':start()
if __name__=='__main__':main()
