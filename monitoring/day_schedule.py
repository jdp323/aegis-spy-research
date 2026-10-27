"""Durable current-slot scheduling, ET and exchange early closes. No backlog."""
from datetime import timedelta
from core.sessions import ET,market_session
from core.idea_config import settings
def due(now,config):
    session=market_session(now);local=now.astimezone(ET);minute=local.hour*60+local.minute
    if session['quality']!='DATA_OK' or not market_session(local.replace(hour=10,minute=0))['active']:return []
    c=settings(config);report=sum(x*y for x,y in zip(map(int,c['report_time'].split(':')),(60,1)));close=session['close_minute'];out=[]
    if report<=minute<report+5:out.append(('PREOPEN',session['date']))
    if 585<=minute<=close-15:
        slot=minute//15*15
        if slot>=585:out.append(('TREND',session['date']+'-'+str(slot)))
    if close+15<=minute<close+20:out.append(('RECAP',session['date']))
    return out
def dispatch(store,now,config,compose,publish):
    result=[]
    for kind,slot in due(now,config):
        key='v5-slot:'+kind+':'+slot
        if store.get(key):continue
        response=compose(kind)
        if not response:continue
        # Reservation precedes transport/outbox. Uncertain delivery never replays a slot.
        reservation={'reserved_at':now.isoformat(),'status':'RESERVED_NO_BLIND_RETRY','producer':'core.idea_service','version':'scheduled-authority-v2'}
        if hasattr(store,'reserve'):
            if not store.reserve(key,reservation):continue
        else:store.put(key,reservation)
        event={'id':'v5-'+kind.lower()+'-'+slot,'kind':'RESEARCH','presentation_version':'owner-compact-v2','tenant':'owner','audience':'SHARED' if config.get('signals',{}).get('shared',False) else 'PRIVATE','text':response,'expires_at':(now+timedelta(minutes=5)).isoformat(),'disable_notification':kind=='TREND' and config.get('trend_lines_silent',True),'alert_type':'TREND_LINE' if kind=='TREND' else kind}
        publish(event);result.append(event)
    return result
