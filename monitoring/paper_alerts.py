"""Capped durable paper research alerts; no live alert routing."""
import hashlib
from core.sessions import ET
from core.signals import option_quote_valid,quote_valid
from data.models import stamp
HEADER='AEGIS — SPY SETUP (PAPER / UNVALIDATED)'
FOOTER='AEGIS does not place orders. Manual review only.'
def signal_text(s,now):
    c=s.get('option_contract');c=c['symbol'] if c and option_quote_valid(c.get('quote',{}),now) else 'UNAVAILABLE'
    return '\n'.join([HEADER,'Mode: '+s.get('paper_mode','OPTIONS_REAL_QUOTES'),'Direction: '+s['direction']+' | '+s['setup_type'],'Score/tier: '+str(s['score'])+' / '+s['tier']+' (uncalibrated)','Entry condition: '+s['entry_condition'],'Underlying range: '+str(s['underlying_entry_range']),'Invalidation: '+str(s['invalidation']),'T1: '+str(s['t1'])+' | T2: '+str(s['t2'])+' | R/R: '+str(s['risk_reward']),'News risk: '+s['news_status'],'Feed quality: '+s.get('feed_quality','UNAVAILABLE'),'Option contract: '+c,'Expires: '+stamp(s['signal_expiry']).astimezone(ET).strftime('%Y-%m-%d %H:%M:%S ET'),FOOTER])
def reserve(store,key,kind,config,now):
    db=store.db;db.execute('CREATE TABLE IF NOT EXISTS paper_notifications(id TEXT PRIMARY KEY,et_day TEXT NOT NULL,kind TEXT NOT NULL,at TEXT NOT NULL)');db.commit();db.execute('BEGIN IMMEDIATE')
    try:
        day=now.astimezone(ET).date().isoformat()
        if db.execute('SELECT 1 FROM paper_notifications WHERE id=?',(key,)).fetchone() or db.execute('SELECT count(*) FROM paper_notifications WHERE et_day=?',(day,)).fetchone()[0]>=config.get('paper_daily_message_cap',8):db.rollback();return False
        db.execute('INSERT INTO paper_notifications VALUES(?,?,?,?)',(key,day,kind,now.isoformat()));db.commit();return True
    except Exception:db.rollback();raise
def emit(store,s,kind,config,enqueue,now,text=None,suffix=''):
    latest=store.get('paper_latest_alerted')
    if kind=='PAPER_UPDATE' and config.get('notifications',{}).get('profile')=='simple' and latest and latest['signal_id']!=s['signal_id']:return False
    key='paper-'+hashlib.sha256((s['signal_id']+s['strategy_version']+kind+suffix).encode()).hexdigest()[:32]
    from monitoring.simple_notifications import enabled
    if not enabled(config,'ideas' if kind=='PAPER_SIGNAL' else 'idea_updates'):return False
    if not reserve(store,key,kind,config,now):return False
    metadata={}
    if kind=='PAPER_UPDATE':metadata['parent_event_id']='paper-'+hashlib.sha256((s['signal_id']+s['strategy_version']+'PAPER_SIGNAL').encode()).hexdigest()[:32]
    if kind=='PAPER_SIGNAL':
        buttons=[{'text':'🚫 Skip','callback_data':'aegis:skip:'+s['signal_id']},{'text':'📊 Chart','callback_data':'aegis:chart:'+s['signal_id']}]
        contract=s.get('option_contract')
        if contract and option_quote_valid(contract.get('quote',{}),now):buttons.append({'text':'✅ I bought','callback_data':'aegis:log:'+s['signal_id']})
        metadata['reply_markup']={'inline_keyboard':[buttons,[{'text':'More ▸','callback_data':'aegis:more:'+s['signal_id']}]]}
    enqueue(store,key,text or (HEADER+'\n'+__import__('core.verdict',fromlist=['short']).short(s,now)+'\n'+FOOTER if config.get('notifications',{}).get('profile')=='simple' else signal_text(s,now)),'SHARED' if config.get('signals',{}).get('shared',False) else 'PRIVATE','owner',kind='RESEARCH',alert_type=kind,signal_id=s['signal_id'],strategy_version=s['strategy_version'],**metadata);return True
def candidate_alert(store,s,config,enqueue,now):
    if not s.get('paper_eligible') or s.get('live_signal_ready') or s.get('actionable') or stamp(s['signal_expiry'])<=now:return False
    store.event('paper-candidate-'+s['signal_id']+'-'+s['strategy_version'],'paper_candidate',s)
    sent=emit(store,s,'PAPER_SIGNAL',config,enqueue,now)
    if sent:store.put('paper_latest_alerted',{'signal_id':s['signal_id'],'at':now.isoformat()})
    return sent
def position_alerts(store,changes,config,enqueue,now):
    for p in changes:
        if config.get('notifications',{}).get('profile')=='simple' and store.get('paper_latest_alerted') and store.get('paper_latest_alerted')['signal_id']!=p['signal_id']:continue
        reason=p.get('update_reason') or p.get('exit_reason') or 'T1_REACHED'
        emit(store,p['signal'],'PAPER_UPDATE',config,enqueue,now,HEADER+'\nPAPER_UPDATE — '+reason+'\nMode: '+p['mode']+'\nModeled USD/share: '+str(p.get('pnl_usd_per_share','UNAVAILABLE'))+'\n'+FOOTER,reason)
def lifecycle(store,q,config,enqueue,now):
    for s in store.events('paper_candidate',1000):
        if config.get('notifications',{}).get('profile')=='simple' and store.get('paper_latest_alerted') and store.get('paper_latest_alerted')['signal_id']!=s['signal_id']:continue
        if store.get('paper_terminal:'+s['signal_id']):continue
        reason='SIGNAL_EXPIRED' if stamp(s['signal_expiry'])<=now else None
        key='research_quote:SPY:iex' if s.get('feed_quality')=='IEX' else 'quote:SPY'
        matching=store.get(key) or q or {}
        expected='alpaca-iex' if s.get('feed_quality')=='IEX' else 'alpaca-sip'
        provider_matches=matching.get('provider')==expected or (expected=='alpaca-sip' and matching.get('provider')=='alpaca')
        px=matching.get('payload',{}).get('mid') if provider_matches and quote_valid(matching,now) else None
        if reason is None and px is not None and s.get('invalidation') is not None and (px-s['invalidation'])*(1 if s['direction']=='CALL' else -1)<=0:reason='SIGNAL_INVALIDATED'
        if reason:
            store.put('paper_terminal:'+s['signal_id'],{'reason':reason,'at':now.isoformat()});emit(store,s,'PAPER_UPDATE',config,enqueue,now,HEADER+'\n'+reason+'\nSignal: '+s['signal_id']+'\n'+FOOTER,reason)
