"""Owner product preference changes; no broker permissions or guest broadcasts."""
import json,os,tempfile
from pathlib import Path
from datetime import timedelta
from data.models import stamp
from core.storage import ROOT
from core.simple_config import validate_new
DEFAULT={'ideas':True,'idea_updates':True,'morning':True,'system':True,'periodic':False,'changes':False,'extended':False,'news':False,'sentiment':False,'trend_lines':True}
def enabled(config,category):
    n=config.get('notifications',{})
    return n.get('categories',{}).get(category,DEFAULT.get(category,False) if n.get('profile','detailed')=='simple' else True)
def alerts(text='',tenant='owner',root=ROOT,store=None):
    if tenant not in ('owner',None):return 'Only the owner can change alert categories.'
    root=Path(root);p=root/'config/upgrade.json';c=json.loads(p.read_text());args=text.lower().split()
    if args and args[0]=='setup':
        from core.idea_config import SETUPS,settings
        if len(args)!=3 or args[1].upper() not in SETUPS or args[2] not in ('on','off'):return 'Use /alerts setup SETUP_NAME on|off'
        name=args[1].upper();c.setdefault('setup_enabled',{})[name]=args[2]=='on'
        overrides=c.setdefault('negative_setup_overrides',[])
        if args[2]=='on' and name not in overrides:overrides.append(name)
        if args[2]=='off' and name in overrides:overrides.remove(name)
        settings(c);validate_new(c)
        with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=p.parent,delete=False) as f:json.dump(c,f,indent=2);tmp=f.name
        os.replace(tmp,p)
        if store:store.audit('setup-alert-'+str(__import__('time').time_ns()),'setup_alert_preference','owner',{'setup':name,'enabled':args[2]=='on'})
        return 'Setup '+name+' alerts '+args[2]+'. NEGATIVE override is explicit when enabled; no live permissions change.'
    if args and args[0]=='silent':
        if len(args)!=2 or args[1] not in ('on','off'):return 'Use /alerts silent on|off'
        c['trend_lines_silent']=args[1]=='on'
        with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=p.parent,delete=False) as f:json.dump(c,f,indent=2);tmp=f.name
        os.replace(tmp,p)
        if store:store.audit('silent-alert-'+str(__import__('time').time_ns()),'notification_preference','owner',{'trend_lines_silent':c['trend_lines_silent']})
        return 'Silent trend lines '+args[1]+'. No live permissions change.'
    if args:
        if len(args)!=2 or args[0] not in DEFAULT or args[1] not in ('on','off'):return 'Use /alerts CATEGORY on|off. Categories: '+', '.join(DEFAULT)
        c.setdefault('notifications',{'profile':'simple','categories':{}}).setdefault('categories',{})[args[0]]=args[1]=='on';validate_new(c)
        with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=p.parent,delete=False) as f:json.dump(c,f,indent=2);tmp=f.name
        os.replace(tmp,p)
        if store:store.audit('alerts-'+__import__('time').time_ns().__str__(),'notification_preference','owner',{'category':args[0],'enabled':args[1]=='on'})
    return 'ALERTS — '+c.get('notifications',{}).get('profile','simple')+'\n'+'\n'.join(k+': '+('ON' if enabled(c,k) else 'OFF') for k in DEFAULT)+'\n/alerts CATEGORY on|off. No live permissions change.'
def calendar_warning(store,news,now,publish,config):
    if not enabled(config,'system') or not news.get('verified_at'):return
    expires=stamp(news['verified_at'])+timedelta(days=7);remaining=(expires-now).total_seconds()
    if 0<=remaining<=3*86400:
        key='calendar-stale-'+__import__('hashlib').sha256(news['verified_at'].encode()).hexdigest()[:24]
        if not store.get(key):
            store.put(key,{'at':now.isoformat()});publish(store,key,'DATA WARNING — Official calendar verification expires within 3 days. Download an official schedule in your browser into config/calendar_import with a provenance JSON sidecar; see research/OWNER_ACTIONS.md, then run python -m news.calendar_updater. Failed imports preserve the good file.','PRIVATE','owner',kind='RESEARCH')

def source_pushes(store,config,now,publish):
    """Opt-in changed news/sentiment only, private to the owner; no quotes or orders."""
    import hashlib
    from news.market_outlook import build,text_for
    from news.reddit import text_for as reddit_text
    for category in ('news','sentiment'):
        if not enabled(config,category):continue
        if category=='news':
            source=build(store,now);items=source.get('news',{}).get('items',[])
            if not items:continue
            evidence=[[x.get('url'),x.get('published_at'),x.get('direction')] for x in items[:6]];text=text_for(source,detail='news')
        else:
            source=store.get('reddit_sentiment') or {}
            if source.get('quality')!='DATA_OK':continue
            evidence={k:source.get(k) for k in ('bias','support','topics','posts_examined','comments_examined')};text=reddit_text(source)
        signature=hashlib.sha256(json.dumps(evidence,sort_keys=True).encode()).hexdigest()[:24]
        if store.get('source-push:'+category)==signature:continue
        publish(store,'source-'+category+'-'+signature,text[:3400],'PRIVATE','owner',kind='RESEARCH')
        store.put('source-push:'+category,signature)
