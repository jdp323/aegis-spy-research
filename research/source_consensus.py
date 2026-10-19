"""Independent source/horizon checks; never a probability or trading gate bypass."""
import hashlib,math
from datetime import datetime,timezone,timedelta
from core.storage import ROOT
from core.sessions import market_session,ET
from data.models import stamp
from data.secondary_spy import URL,parse_daily
from features.indicators import ema
VERSION='spy-independent-source-context-v1'
def daily_context(doc,now=None,root=None):
    now=now or datetime.now(timezone.utc);root=root or ROOT
    out={'provider':'Stooq','status':'UNAVAILABLE','horizon':'COMPLETED_DAILY','reason':'SOURCE_OR_PROVENANCE_UNAVAILABLE','action':'NO TRADE','version':VERSION}
    try:
        if doc.get('source')!=URL or doc.get('provider')!='Stooq' or doc.get('status')!='DAILY_HISTORY_RECEIVED':return out
        if not 0<=(now-stamp(doc['fetched_at'])).total_seconds()<=86400:return {**out,'reason':'DAILY_FETCH_STALE'}
        digest=doc['sha256']
        if len(digest)!=64 or any(x not in '0123456789abcdef' for x in digest):return out
        raw=(root/'data/public_cache'/(digest+'.csv')).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=digest or parse_daily(raw,stamp(doc['fetched_at']))[-260:]!=doc['rows']:return out
        expected=None
        for n in range(1,8):
            day=now.astimezone(ET).date()-timedelta(days=n)
            session=market_session(datetime.combine(day,datetime.min.time(),ET)+timedelta(hours=12))
            if session['quality']!='DATA_OK':return {**out,'reason':'CALENDAR_UNAVAILABLE'}
            if session['active']:expected=day.isoformat();break
        rows=[r for r in doc['rows'] if r['date']<now.astimezone(ET).date().isoformat()]
        if not rows or rows[-1]['date']!=expected:return {**out,'reason':'LATEST_COMPLETED_SESSION_MISSING'}
        if len(rows)<50:return {**out,'reason':'DAILY_WARMUP_INSUFFICIENT'}
        tail=rows[-60:]
        for a,b in zip(tail,tail[1:]):
            start=datetime.fromisoformat(a['date']).date();end=datetime.fromisoformat(b['date']).date()
            for n in range(1,(end-start).days):
                s=market_session(datetime.combine(start+timedelta(days=n),datetime.min.time(),ET)+timedelta(hours=12))
                if s['quality']!='DATA_OK' or s['active']:return {**out,'reason':'DAILY_HISTORY_GAP_OR_CALENDAR_UNAVAILABLE'}
        close=[r['close'] for r in rows];e20=ema(close,20)[-1];e50=ema(close,50)[-1]
        changes=[b-a for a,b in zip(close,close[1:])];gain=sum(max(x,0) for x in changes[:14])/14;loss=sum(max(-x,0) for x in changes[:14])/14
        for x in changes[14:]:gain=(gain*13+max(x,0))/14;loss=(loss*13+max(-x,0))/14
        rsi=50 if gain==loss==0 else 100 if loss==0 else 100-100/(1+gain/loss)
        trend='UPWARD' if close[-1]>e20>e50 else 'DOWNWARD' if close[-1]<e20<e50 else 'MIXED'
        return {**out,'status':'DAILY_RESEARCH_ONLY','reason':'DESCRIPTIVE_NOT_PREDICTIVE','as_of_date':rows[-1]['date'],'fetched_at':doc['fetched_at'],'sha256':digest,'trend':trend,'close':close[-1],'ema20':e20,'ema50':e50,'rsi14':rsi,'momentum5_pct':(close[-1]/close[-6]-1)*100,'adjustments':'UNVERIFIED','bars':len(rows)}
    except (OSError,ValueError,KeyError,TypeError,OverflowError):return out
def compare_intraday(a,b,now=None):
    now=now or datetime.now(timezone.utc)
    out={'status':'NOT_COMPARABLE','reason':'MISSING_OR_UNMATCHED_RECENT_BARS','tolerance_pct':.15}
    try:
        x=a['levels'];y=b['levels'];tx=stamp(x['last_completed_bar_at']);ty=stamp(y['last_completed_bar_at'])
        if a['data_status']!='RESEARCH_DATA_RECEIVED' or b['data_status']!='RESEARCH_DATA_RECEIVED' or a['source']==b['source']:return out
        if x['session_date']!=y['session_date'] or tx!=ty or not market_session(tx)['active'] or not 0<=(now-tx-timedelta(minutes=5)).total_seconds()<=900:return out
        for d in (a,b):
            if not 0<=(now-stamp(d['source_fetched_at'])).total_seconds()<=600:return out
        values=(x['last_close'],y['last_close'])
        if any(type(v) not in (float,int) or not math.isfinite(v) or v<=0 for v in values):return out
        difference=abs(values[0]/values[1]-1)*100
        return {**out,'status':'AGREEMENT' if difference<=.15 else 'DISAGREEMENT','reason':'MATCHED_COMPLETED_5M_CLOSES','bar':tx.isoformat(),'difference_pct':difference,'sources':[a['source'],b['source']]}
    except (KeyError,ValueError,TypeError):return out
def message_context(snapshot,trend=None):
    m=snapshot.get('multi_source') or {};d=m.get('daily') or {};c=m.get('intraday_comparison') or {}
    if d.get('status')=='DAILY_RESEARCH_ONLY':
        label=d['trend'];alignment=''
        if trend in ('UPWARD 5m STRUCTURE','DOWNWARD 5m STRUCTURE') and label in ('UPWARD','DOWNWARD'):
            alignment=' Same direction as recent5m structure.' if trend.startswith(label) else ' Different from recent5m structure; horizons conflict.'
        daily='DAILY VIEW: Stooq '+label+' as of '+d['as_of_date']+' | EMA20 $%.2f / EMA50 $%.2f | RSI14 %.1f.'%(d['ema20'],d['ema50'],d['rsi14'])+alignment+' Historical daily bars; adjustments unverified.'
    else:daily='DAILY VIEW: Stooq unavailable — '+d.get('reason','not checked')+'.'
    comparison='SOURCE CHECK: '+c.get('status','NOT_COMPARABLE')+'. Two fresh matching intraday sources are '+('available; agreement is not proof of real-time data.' if c.get('status')=='AGREEMENT' else 'not established; no confirmation claimed.')
    return daily+'\n'+comparison
