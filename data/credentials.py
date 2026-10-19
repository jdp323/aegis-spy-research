"""Optional local DPAPI market-data setup; never returns secrets to a console."""
import json,os,getpass,sys,re
from pathlib import Path
from core.storage import ROOT
from monitoring.vault import transform
from core.runtime_paths import private_directory
PATH=private_directory()/'market_data.dpapi'
NAMES=('APCA_API_KEY_ID','APCA_API_SECRET_KEY')

def validate(obj):
    if not isinstance(obj,dict) or set(obj)!=set(NAMES):raise ValueError('Invalid market-data key fields')
    if any(not isinstance(obj[k],str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,128}',obj[k]) for k in NAMES):raise ValueError('Invalid market-data key format')
    return obj

def child_environment(base=None):
    """Only worker/stream callers consume decrypted keys inside their process."""
    env=dict(os.environ if base is None else base)
    if all(env.get(k) for k in NAMES):return env
    if not PATH.exists():return env
    try:
        keys=validate(json.loads(transform(PATH.read_bytes(),True)))
        for k in NAMES:env[k]=keys[k]
        return env
    except Exception:raise RuntimeError('MARKET_DATA_ENCRYPTED_CONFIG_UNREADABLE') from None

def configured():return {'encrypted_config_present':PATH.is_file(),'environment_pair_present':all(bool(os.environ.get(k)) for k in NAMES)}

def save(keys):
    """Encrypt before exclusive creation; shared by terminal and one-shot local setup."""
    if PATH.exists():raise RuntimeError('EXISTING_CONFIGURATION_PRESERVED')
    raw=json.dumps(validate(keys)).encode();encrypted=transform(raw)
    if transform(encrypted,True)!=raw:raise RuntimeError('ENCRYPTION_VERIFICATION_FAILED')
    PATH.parent.mkdir(parents=True,exist_ok=True)
    with PATH.open('xb') as f:f.write(encrypted)

def configure():
    # Explicit interactive owner entry, no arguments, stdout load or stdin file.
    if not sys.stdin.isatty():raise RuntimeError('INTERACTIVE_LOCAL_TERMINAL_REQUIRED')
    if PATH.exists():raise RuntimeError('EXISTING_CONFIGURATION_PRESERVED')
    print('Alpaca market-data API keys only. No brokerage password or Telegram token.')
    keys=validate({NAMES[0]:getpass.getpass('API key ID (hidden): ').strip(),NAMES[1]:getpass.getpass('API secret (hidden): ').strip()})
    save(keys)
    print('ENCRYPTED_MARKET_DATA_CONFIGURATION_SAVED. Restart AEGIS to test provider access.')

if __name__=='__main__':
    try:
        if len(sys.argv)!=2 or sys.argv[1] not in ('configure','status'):raise RuntimeError('Use configure or status; no secret arguments accepted')
        if sys.argv[1]=='configure':configure()
        else:print(json.dumps(configured()))
    except Exception:
        print('Market-data setup unavailable or existing configuration preserved. No keys logged.',file=sys.stderr);raise SystemExit(1)
