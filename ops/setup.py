"""Local first-run setup. Never print credentials or accept them as arguments."""
import argparse, getpass, json, os, re, secrets, sys
from pathlib import Path
from urllib.request import Request, build_opener
from core.storage import ROOT
from core.runtime_paths import private_directory
from monitoring.telegram_test import NoRedirect

def initialize(root=ROOT):
    root=Path(root)
    for folder in ('runtime','logs','daily_reports','research/verification'):(root/folder).mkdir(parents=True,exist_ok=True)
    target=root/'config/news_calendar.json'
    if not target.exists():target.write_bytes((root/'config/news_calendar.example.json').read_bytes())
    return {'initialized':True,'calendar':'LOCAL_UNVERIFIED_UNTIL_REFRESHED','live_signals':False}

def safe_status(root=ROOT,private=None):
    root=Path(root);private=Path(private or private_directory())
    return {'telegram_encrypted_store_present':(private/'telegram.dpapi').is_file(),
      'market_encrypted_store_present':(private/'market_data.dpapi').is_file(),
      'bot_identity_config_present':(root/'config/telegram.json').is_file(),
      'calendar_local_file_present':(root/'config/news_calendar.json').is_file(),
      'note':'Presence is not authentication, entitlement, freshness or readiness. No AI key is required.'}

def telegram_api(token):
    opener=build_opener(NoRedirect())
    def call(method,body):
        request=Request('https://api.telegram.org/bot'+token+'/'+method,
            data=json.dumps(body).encode(),headers={'Content-Type':'application/json'},method='POST')
        with opener.open(request,timeout=20) as response:result=json.load(response)
        if result.get('ok') is not True:raise ValueError('TELEGRAM_REJECTED')
        return result['result']
    return call

def pair(token,call,challenge,wait,root=ROOT,private=None,protect=None):
    # A newly generated challenge must be sent by the owner in a private chat.
    root=Path(root);private=Path(private or private_directory());target=private/'telegram.dpapi'
    if target.exists():raise ValueError('EXISTING_CONFIGURATION_PRESERVED')
    identity=call('getMe',{})
    if identity.get('is_bot') is not True or not re.fullmatch(r'[A-Za-z0-9_]{5,32}',identity.get('username','')):raise ValueError('INVALID_BOT_IDENTITY')
    if not isinstance(identity.get('id'),int) or identity['id']<=0:raise ValueError('INVALID_BOT_IDENTITY')
    wait(identity['username'],challenge)
    updates=call('getUpdates',{'limit':100,'timeout':0})
    chats={str(u['message']['chat']['id']) for u in updates
        if u.get('message',{}).get('text')==challenge
        and u['message'].get('chat',{}).get('type')=='private'
        and str(u['message'].get('from',{}).get('id'))==str(u['message']['chat'].get('id'))}
    if len(chats)!=1:raise ValueError('PAIRING_NOT_UNIQUE_OR_MISSING')
    chat=chats.pop()
    if not chat.isdigit() or int(chat)<=0:raise ValueError('INVALID_PRIVATE_DESTINATION')
    destination=call('getChat',{'chat_id':chat})
    if destination.get('type')!='private' or str(destination.get('id'))!=chat:raise ValueError('PRIVATE_DESTINATION_MISMATCH')
    if protect is None:
        from monitoring.vault import transform
        protect=transform
    raw=json.dumps({'token':token,'chat_id':chat}).encode();encrypted=protect(raw)
    if protect(encrypted,True)!=raw:raise ValueError('ENCRYPTION_ROUNDTRIP_FAILED')
    private.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(encrypted)
    config=root/'config/telegram.json';config.parent.mkdir(exist_ok=True,parents=True)
    config.write_text(json.dumps({'username':identity['username']},indent=2),encoding='utf-8')
    return {'status':'ENCRYPTED_CONFIGURATION_SAVED','sent':False,'note':'Restart the local services to verify ongoing operation.'}

def configure_telegram():
    if os.name!='nt':raise ValueError('WINDOWS_DPAPI_REQUIRED')
    if not sys.stdin.isatty():raise ValueError('INTERACTIVE_LOCAL_TERMINAL_REQUIRED')
    if (private_directory()/'telegram.dpapi').exists():raise ValueError('EXISTING_CONFIGURATION_PRESERVED')
    token=getpass.getpass('Your Telegram bot token (hidden): ').strip()
    if not re.fullmatch(r'[0-9]+:[A-Za-z0-9_-]{20,}',token):raise ValueError('INVALID_TOKEN_FORMAT')
    challenge='AEGIS-PAIR-'+secrets.token_hex(16)
    def wait(username,text):
        print('Send this exact message to @'+username+' in your PRIVATE Telegram chat:')
        print(text);input('Then press Enter here: ')
    return pair(token,telegram_api(token),challenge,wait)

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('init','status','telegram','market'))
    args=parser.parse_args(argv)
    try:
        if args.mode=='init':result=initialize()
        elif args.mode=='status':result=safe_status()
        elif args.mode=='telegram':result=configure_telegram()
        else:
            from data.credentials import configure
            configure();return 0
        print(json.dumps(result,indent=2));return 0
    except Exception:
        # API exception strings may contain a token-bearing URL. Do not echo them.
        print('SETUP_FAILED: no credentials logged. Existing configuration is preserved. Check SETUP.md for pairing, webhook, network and Windows requirements.',file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
