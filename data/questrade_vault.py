"""DPAPI refresh journal. Rotated secrets are encrypted before any access-token use."""
import json,os,threading,time,contextlib
from pathlib import Path
from datetime import datetime,timezone,timedelta
from monitoring.vault import transform
from core.storage import ROOT
from data.models import stamp
from core.runtime_paths import private_directory
PATH=private_directory()/'questrade.dpapi'
_mutex=threading.RLock()
@contextlib.contextmanager
def locked(path=PATH,timeout=10):
    """Per-process mutex plus OS byte lock; released automatically after a crash."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with _mutex,open(str(path)+'.lock','a+b') as f:
        f.seek(0,os.SEEK_END)
        if f.tell()==0:f.write(b'0');f.flush()
        deadline=time.monotonic()+timeout
        while True:
            try:
                f.seek(0)
                if os.name=='nt':
                    import msvcrt
                    msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
                else:
                    import fcntl
                    fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic()>=deadline:raise RuntimeError('QUESTRADE_LOCK_TIMEOUT') from None
                time.sleep(.05)
        try:yield
        finally:
            f.seek(0)
            if os.name=='nt':msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(f,fcntl.LOCK_UN)
class Vault:
    def __init__(self,path=PATH,crypt=transform):self.path=Path(path);self.crypt=crypt
    def load(self):
        if not self.path.exists():return None
        try:return json.loads(self.crypt(self.path.read_bytes(),True))
        except Exception:raise RuntimeError('QUESTRADE_VAULT_UNREADABLE') from None
    def save(self,state):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        raw=json.dumps(state,allow_nan=False).encode();sealed=self.crypt(raw)
        if self.crypt(sealed,True)!=raw:raise RuntimeError('QUESTRADE_ENCRYPTION_FAILED')
        temp=self.path.with_suffix('.pending')
        try:
            with temp.open('wb') as f:f.write(sealed);f.flush();os.fsync(f.fileno())
            os.replace(temp,self.path)
        finally:
            if temp.exists():temp.unlink()
    def configure(self,token,now=None):
        import re
        if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_.~-]{16,2048}',token):raise ValueError('INVALID_REFRESH_FORMAT')
        now=now or datetime.now(timezone.utc)
        with locked(self.path):
            # Manual owner entry is the explicit recovery path; preserve prior encrypted state.
            if self.path.exists():
                backup=self.path.with_name(self.path.name+'.'+now.strftime('%Y%m%dT%H%M%S%fZ')+'.bak');backup.write_bytes(self.path.read_bytes())
            self.save({'refresh_token':token,'entered_at':now.isoformat(),'refresh_policy_deadline':(now+timedelta(hours=72)).isoformat(),'refresh_in_progress':False})
    def status(self,now=None):
        now=now or datetime.now(timezone.utc)
        state=self.load()
        if not state:return {'provider':'questrade','status':'QUESTRADE_NOT_CONFIGURED'}
        deadline=stamp(state['refresh_policy_deadline']);remaining=(deadline-now).total_seconds()
        return {'provider':'questrade','status':'QUESTRADE_REFRESH_UNCERTAIN' if state.get('refresh_in_progress') else 'QUESTRADE_TOKEN_EXPIRED' if remaining<=0 else 'CONFIGURED_UNVERIFIED','token_refreshed_at':state.get('token_refreshed_at'),'token_expires_at':deadline.isoformat(),'refresh_expiry_basis':'CONSERVATIVE_72H_POLICY; provider refresh expiry not supplied','token_age_hours':(now-stamp(state.get('token_refreshed_at',state['entered_at']))).total_seconds()/3600,'hours_until_policy_expiry':remaining/3600}
