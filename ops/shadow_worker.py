"""Independent, low-priority shadow supervisor; no model imports in AEGIS worker."""
import os,sys,json,time,subprocess,sqlite3,tempfile,threading
from pathlib import Path
from datetime import datetime,timezone
from core.storage import ROOT
from core.readonly_state import ReadOnlyState
from research.shadow_forecast import prepare,validate_result,ShadowLog

TIMEOUT_SECONDS=45
MEMORY_BYTES=768*1024*1024
MINIMUM_FREE_BYTES=1536*1024*1024

def available_memory():
    if os.name=='nt':
        import ctypes
        class Status(ctypes.Structure):
            _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in ('total','available','page_total','page_available','virtual_total','virtual_available','extended')]
        s=Status();s.length=ctypes.sizeof(s)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s)):return 0
        return s.available
    try:return os.sysconf('SC_AVPHYS_PAGES')*os.sysconf('SC_PAGE_SIZE')
    except (ValueError,OSError):return 0

def environment():
    env={k:v for k,v in os.environ.items() if k.upper() in ('PATH','SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','LOCALAPPDATA','USERPROFILE')}
    env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',WANDB_MODE='disabled',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONIOENCODING='utf-8')
    return env

def windows_job(process,limit):
    """Kill-on-close plus per-process committed-memory bound, before inference."""
    import ctypes
    from ctypes import wintypes
    class Basic(ctypes.Structure):
        _fields_=[('process_time',ctypes.c_longlong),('job_time',ctypes.c_longlong),('flags',wintypes.DWORD),('min_work',ctypes.c_size_t),('max_work',ctypes.c_size_t),('active',wintypes.DWORD),('affinity',ctypes.c_size_t),('priority',wintypes.DWORD),('scheduling',wintypes.DWORD)]
    class IO(ctypes.Structure):_fields_=[(n,ctypes.c_ulonglong) for n in ('read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes')]
    class Extended(ctypes.Structure):_fields_=[('basic',Basic),('io',IO),('process_memory',ctypes.c_size_t),('job_memory',ctypes.c_size_t),('peak_process',ctypes.c_size_t),('peak_job',ctypes.c_size_t)]
    k=ctypes.WinDLL('kernel32',use_last_error=True);k.CreateJobObjectW.restype=wintypes.HANDLE;k.CreateJobObjectW.argtypes=[ctypes.c_void_p,wintypes.LPCWSTR];k.SetInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD];k.AssignProcessToJobObject.argtypes=[wintypes.HANDLE,wintypes.HANDLE];k.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=k.CreateJobObjectW(None,None);v=Extended();v.basic.flags=0x2000|0x100;v.process_memory=limit
    if not handle or not k.SetInformationJobObject(handle,9,ctypes.byref(v),ctypes.sizeof(v)) or not k.AssignProcessToJobObject(handle,wintypes.HANDLE(int(process._handle))):
        if handle:k.CloseHandle(handle)
        raise OSError('MODEL_RESOURCE_CONTAINMENT_UNAVAILABLE')
    return lambda:k.CloseHandle(handle)

def bounded(command,request,timeout=TIMEOUT_SECONDS,memory=available_memory,limit=MEMORY_BYTES):
    free=memory();start=time.monotonic()
    if free<MINIMUM_FREE_BYTES:return {'status':'BLOCKED_RESOURCE_HEADROOM','free_bytes':free,'minimum_free_bytes':MINIMUM_FREE_BYTES,'runtime_seconds':time.monotonic()-start}
    # Child waits for stdin; attach the memory job before releasing work.
    flags=(subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS) if os.name=='nt' else 0
    output=tempfile.TemporaryFile();errors=tempfile.TemporaryFile()
    p=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.PIPE,stdout=output,stderr=errors,env=environment(),creationflags=flags)
    close_job=lambda:None
    try:
        if os.name=='nt':close_job=windows_job(p,limit)
        else:
            import resource
            resource.prlimit(p.pid,resource.RLIMIT_AS,(limit,limit))
        raw=json.dumps(request).encode()
        if len(raw)>524288:raise ValueError('INPUT_TOO_LARGE')
        # Bounded files avoid accumulating an untrusted model's stdout in RAM.
        def communicate():
            try:p.communicate(raw)
            except (OSError,ValueError):pass
        sender=threading.Thread(target=communicate,daemon=True);sender.start();failure=None
        while p.poll() is None:
            if time.monotonic()-start>=timeout:failure='TIMEOUT';break
            if memory()<512*1024*1024:failure='MEMORY_HEADROOM_LOST';break
            if os.fstat(output.fileno()).st_size>2*1024*1024 or os.fstat(errors.fileno()).st_size>2*1024*1024:failure='OUTPUT_TOO_LARGE';break
            time.sleep(.02)
        if failure:
            p.kill();sender.join(2);p.wait(timeout=2)
            return {'status':failure,'runtime_seconds':time.monotonic()-start,'budget_seconds':timeout}
        sender.join(2);output.seek(0);errors.seek(0);out=output.read(2*1024*1024+1);err=errors.read(2*1024*1024+1)
        if p.returncode:return {'status':'MODEL_PROCESS_FAILED','exit_code':p.returncode,'stderr_sha256':__import__('hashlib').sha256(err).hexdigest(),'runtime_seconds':time.monotonic()-start}
        if len(out)>2*1024*1024:return {'status':'OUTPUT_TOO_LARGE','runtime_seconds':time.monotonic()-start}
        return {'status':'COMPLETED','result':json.loads(out),'runtime_seconds':time.monotonic()-start}
    except (ValueError,OSError) as e:
        p.kill();p.wait(timeout=2);return {'status':'CONTAINMENT_OR_PROTOCOL_FAILED','error_type':type(e).__name__,'runtime_seconds':time.monotonic()-start}
    finally:close_job();output.close();errors.close()

def collect_request(store,now,horizon):
    """Authorized native bars, observed now; never assert an unknown receipt."""
    from features.indicators import normalize
    for feed in ('sip','iex'):
        raw=(store.get('history_frames:'+feed) or {}).get('5m',[])
        bars=normalize(raw,5,now)
        if len(bars)<78:continue
        rows=[]
        for b in bars[-78:]:
            start=datetime.fromtimestamp(b['timestamp'],timezone.utc)
            rows.append({**b,'symbol':'SPY','feed_quality':feed.upper(),'origin':'PROVIDER_NATIVE_AGGREGATE','start_at':start.isoformat(),'received_at':now.isoformat(),'receipt_meaning':'FIRST_SHADOW_READ_OBSERVATION; original provider receipt unavailable'})
        try:
            request=prepare(rows,feed.upper(),now,horizon)
            from collections import defaultdict
            from research.shadow_forecast import earlier_session_baseline
            history=defaultdict(list)
            for b in bars:
                start=datetime.fromtimestamp(b['timestamp'],timezone.utc)
                history[start.astimezone(__import__('core.sessions',fromlist=['ET']).ET).date().isoformat()].append({**b,'start_at':start.isoformat(),'feed_quality':feed.upper()})
            cutoff=__import__('data.models',fromlist=['stamp']).stamp(request['input_cutoff']);end=__import__('data.models',fromlist=['stamp']).stamp(request['target_at'])
            request['baselines']={'time_of_day':earlier_session_baseline(history,cutoff,rows[-1]['close'],int((end-cutoff).total_seconds()/60),feed=feed.upper()),'no_change_price':rows[-1]['close']}
            from core.idea_service import context
            from core.directional_research import view
            request['baselines']['deterministic_direction']=view(context(store,now),now).get('trend','DATA UNAVAILABLE')
            return request
        except ValueError:continue
    raise ValueError('GENUINE_CURRENT_CONTEXT_UNAVAILABLE')

def step(root=ROOT,now=None):
    now=now or datetime.now(timezone.utc);runtime=Path(root)/'runtime';runtime.mkdir(exist_ok=True)
    home=Path(root)/'.shadow-model';python=home/('venv/Scripts/python.exe' if os.name=='nt' else 'venv/bin/python')
    status={'at':now.isoformat(),'state':'SHADOW_ONLY','entry_control':False,'budget_seconds':TIMEOUT_SECONDS,'memory_limit_bytes':MEMORY_BYTES,'free_bytes':available_memory()}
    if not python.is_file() or not (home/'ASSETS.json').is_file():status['state']='MODEL_ENVIRONMENT_UNAVAILABLE'
    elif status['free_bytes']<MINIMUM_FREE_BYTES:status['state']='BLOCKED_RESOURCE_HEADROOM'
    else:
        s=ReadOnlyState(Path(root)/'runtime/aegis.sqlite');log=ShadowLog(runtime/'shadow_forecasts.sqlite')
        try:
            for horizon in ('H60','H120','SESSION'):
                try:request=collect_request(s,now,horizon)
                except ValueError as e:status['state']=str(e);continue
                if not log.append(request['id'],'REQUEST',request,now):continue
                result=bounded([str(python),'-X','utf8','-m','ops.kronos_infer',str(home)],request)
                completed=datetime.now(timezone.utc)
                if result['status']=='COMPLETED':
                    try:result['validated']=validate_result(request,result['result'],completed)
                    except ValueError as e:result.update(status='REJECTED_MODEL_OUTPUT',reason=str(e))
                log.append(request['id']+':result','RESULT',result,completed);status['state']=result['status']
        finally:s.close();log.close()
    target=runtime/'shadow_health.json';temp=target.with_suffix('.tmp');temp.write_text(json.dumps(status));temp.replace(target)
    return status

def main():
    last=None
    while not (ROOT/'runtime/shutdown.request').exists():
        now=datetime.now(timezone.utc);slot=now.strftime('%Y-%m-%dT%H:')+str(now.minute//15)
        if slot!=last:
            try:step(now=now)
            except Exception as error:print(json.dumps({'at':now.isoformat(),'state':'SHADOW_UNAVAILABLE','error_type':type(error).__name__}),flush=True)
            last=slot
        # Separate local evidence job. Never delays the market worker or sends.
        local=now.astimezone(__import__('core.sessions',fromlist=['ET']).ET)
        session=__import__('core.sessions',fromlist=['market_session']).market_session(local.replace(hour=12,minute=0))
        if session['active'] and session['close_minute']+20<=local.hour*60+local.minute<session['close_minute']+25:
            day=local.date().isoformat();folder=ROOT/'daily_reports'
            if not list(folder.glob('MASTER_SESSION_'+day+'_*.json')):
                try:
                    from ops.master_session import collect
                    from research.shadow_forecast import sha
                    result=collect(day);body=json.dumps(result,allow_nan=False);folder.mkdir(exist_ok=True)
                    with (folder/('MASTER_SESSION_'+day+'_'+sha(result)[:12]+'.json')).open('x') as f:f.write(body)
                except (OSError,ValueError,sqlite3.Error):pass
        time.sleep(5)
if __name__=='__main__':main()
