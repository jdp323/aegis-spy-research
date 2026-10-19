"""Measured setup diagnostics, aggregated per setup/direction/minute.

14-day active window; older rows remain archival evidence. Traces describe the
existing detector; they do not upgrade incomplete data into strategy evidence.
"""
import sqlite3,json,hashlib,statistics
from datetime import timezone,timedelta
from core.idea_config import settings
from data.models import finite,stamp

# Bounded display categories. Exact measurements/text stay in their raw trace;
# historical strings never become claims that an unrecorded predicate was known.
BLOCKER_CODES=frozenset({'PROVIDER_MISMATCH','RECEIPT_AFTER_CLOCK','SOURCE_AFTER_CLOCK','SOURCE_RECEIPT_SKEW','SOURCE_TOO_OLD','RECEIPT_TOO_OLD','QUALITY_ENTITLEMENT_OR_BID_ASK_INVALID','QUOTE_TIMESTAMP_UNAVAILABLE','CLOCK_OFFSET','CLOCK_OFFSET_UNAVAILABLE','STREAM_STATE','STREAM_DOWN','HEARTBEAT_AGE','HEARTBEAT_UNAVAILABLE','BAR_TAIL_AGE','BAR_END_AGE','BAR_TAIL_SHORT','BAR_TAIL_GAP','BAR_TAIL_UNAVAILABLE','BAR_CONTINUITY','BAR_HISTORY','BAR_HISTORY_INVALID','CURRENT_SESSION_BARS','INSUFFICIENT_BARS','CONTINUITY_UNAVAILABLE','NEWS_DATA_UNAVAILABLE','NEWS_BLACKOUT','EARLY_SETUP_DISABLED','SETUP_INPUTS_UNAVAILABLE'})
CHECK_NAMES=frozenset({'candle','volume_ratio','structure','higher_frame','reward_risk','price_vs_vwap','trigger_distance'})
LEGACY_PREFIXES=(('Quote rejected: provider mismatch','PROVIDER_MISMATCH'),('Quote rejected: receipt time after evaluation clock','RECEIPT_AFTER_CLOCK'),('Quote rejected: source time after evaluation clock','SOURCE_AFTER_CLOCK'),('Quote rejected: source/receipt skew exceeds accepted tolerance','SOURCE_RECEIPT_SKEW'),('Quote rejected: source age exceeds 5 s','SOURCE_TOO_OLD'),('Quote rejected: receipt age exceeds 5 s','RECEIPT_TOO_OLD'),('Quote rejected: quality, entitlement or bid/ask invalid','QUALITY_ENTITLEMENT_OR_BID_ASK_INVALID'),('Quote rejected: quote timestamp unavailable','QUOTE_TIMESTAMP_UNAVAILABLE'),('feed heartbeat not fresh: signed heartbeat age','HEARTBEAT_AGE'),('feed heartbeat unavailable','HEARTBEAT_UNAVAILABLE'),('completed bars not fresh: signed end age','BAR_END_AGE'),('contiguous history missing: no completed current-session bars','BAR_TAIL_UNAVAILABLE'),('contiguous history missing: UNCONFIRMED_MINUTE_GAP','BAR_TAIL_GAP'),('contiguous history missing: CONFIRMED_EMPTY_LIMIT_EXCEEDED','BAR_TAIL_GAP'),('opening range forming; insufficient completed history','BAR_TAIL_SHORT'),('stream down: ','STREAM_DOWN'),('clock offset beyond tolerance','CLOCK_OFFSET'))

def reason_codes(trace):
    """Stable counted reasons; legacy textual inference is explicitly labelled."""
    if trace.get('blocker'):
        code=trace.get('blocker_code')
        if code:return [code if code in BLOCKER_CODES else 'EXPLICIT_OTHER_PREDICATE']
        text=trace['blocker']
        if text in BLOCKER_CODES:return ['LEGACY_STORED_'+text]
        if isinstance(text,str):
            if text.startswith('data not fresh — '):text=text[len('data not fresh — '):]
            for prefix,code in LEGACY_PREFIXES:
                if text.startswith(prefix):return ['LEGACY_INFERRED_'+code]
        return ['LEGACY_UNKNOWN_BLOCKER']
    return ['CHECK_'+name.upper() if name in CHECK_NAMES else 'UNKNOWN_FAILED_CHECK' for name,value in trace.get('checks',{}).items() if value.get('state')=='FAIL']
from strategies.idea_setups import levels,VERSION

def measure(ctx,news,config,now):
    bars=ctx.get('bars') or [];features=ctx.get('features') or {};f=features.get('1m',{});o=features.get('opening_range') or {};q=ctx.get('quote') or {};px=q.get('payload',{}).get('mid');early=ctx.get('early',False);c=settings(config);out=[]
    for name,enabled in c['setup_enabled'].items():
        if not enabled:continue
        signs=(1,) if name in ('OPENING_RANGE_BREAKOUT','VWAP_RECLAIM','SUPPORT_BOUNCE') else (-1,) if name in ('OPENING_RANGE_BREAKDOWN','VWAP_REJECTION','RESISTANCE_REJECTION') else (1,-1)
        for sign in signs:
            checks={key:{'state':'NOT_EVALUATED','value':None,'threshold':threshold} for key,threshold in {'candle':'signed close change > 0','volume_ratio':1.5 if early else 1.2,'structure':'setup-specific completed candle trigger','higher_frame':'known opposing frames < 2; missing frames never agree','reward_risk':c['min_rr'],'price_vs_vwap':'signed price - VWAP > 0','trigger_distance':'signed price - trigger >= 0 AND abs(price-last close) <= .5 ATR'}.items()}
            blocker=ctx.get('reason') or ('NEWS_DATA_UNAVAILABLE' if news.get('quality')!='DATA_OK' else 'NEWS_BLACKOUT' if news.get('risk')=='HIGH' else None)
            blocker_code=ctx.get('failed_predicate') if ctx.get('reason') else blocker
            if not blocker and len(bars)>=15 and all(finite(x) and x>0 for x in (px,f.get('atr14'),f.get('vwap_approx'),f.get('previous_vwap_approx'))):
                last,prev=bars[-1],bars[-2];atr=f['atr14'];vw=f['vwap_approx'];pv=f['previous_vwap_approx'];boundary=o.get('high' if sign==1 else 'low');ema=f.get('ema9');support=f.get('support' if sign==1 else 'resistance')
                baseline=[b['volume'] for b in (bars[:15] if early else bars[-11:-1]) if not b.get('synthetic')];recent=statistics.mean(baseline) if baseline else 0;ratio=last['volume']/recent if recent>0 else None
                opposing='BEAR' if sign==1 else 'BULL';frames={k:features.get(k,{}).get('trend','UNAVAILABLE') for k in ('15m','30m','1h')};against=sum(v==opposing for v in frames.values())
                trigger=boundary if name.startswith('OPENING_RANGE') or name=='BREAKOUT_RETEST' else vw if name.startswith('VWAP') else ema if name=='TREND_CONTINUATION' else support
                structure=None
                if name.startswith('OPENING_RANGE') and finite(boundary):structure=(last['close']-boundary)*sign>0 and (prev['close']-boundary)*sign<=0
                elif name.startswith('VWAP'):structure=not early and (prev['close']-pv)*sign<=0 and (last['close']-vw)*sign>0
                elif name=='TREND_CONTINUATION' and finite(ema):structure=not early and features.get('15m',{}).get('trend')==('BULL' if sign==1 else 'BEAR') and features.get('1h',{}).get('trend')==('BULL' if sign==1 else 'BEAR') and (prev['close']-ema)*sign<=0<(last['close']-ema)*sign
                elif name in ('SUPPORT_BOUNCE','RESISTANCE_REJECTION') and finite(support):structure=not early and (last['low']<=support<last['close'] if sign==1 else last['high']>=support>last['close'])
                elif name=='BREAKOUT_RETEST' and finite(boundary):structure=not early and (prev['close']-boundary)*sign>0 and (last['low']<=boundary<last['close'] if sign==1 else last['high']>=boundary>last['close'])
                lv=levels(px,min(last['low'],prev['low']) if sign==1 else max(last['high'],prev['high']),sign,atr,f,config)
                values={'candle':((last['close']-prev['close'])*sign,(last['close']-prev['close'])*sign>0),'volume_ratio':(ratio,ratio is not None and ratio>=checks['volume_ratio']['threshold']),'structure':({'matched':structure,'trigger':trigger},structure is True),'higher_frame':({'frames':frames,'known_opposing':against,'unavailable':[k for k,v in frames.items() if v in (None,'UNAVAILABLE')]},against<2),'reward_risk':(lv['risk_reward'] if lv else None,lv is not None),'price_vs_vwap':((px-vw)*sign,(px-vw)*sign>0),'trigger_distance':({'signed_trigger_distance':(px-trigger)*sign if finite(trigger) else None,'distance_from_close':abs(px-last['close']),'maximum_distance':.5*atr},finite(trigger) and (px-trigger)*sign>=0 and abs(px-last['close'])<=.5*atr)}
                for key,(value,passed) in values.items():checks[key].update(state='PASS' if passed else 'FAIL',value=value)
                if early and (not name.startswith('OPENING_RANGE') or not c['early_session_ideas']):blocker='EARLY_SETUP_DISABLED';blocker_code=blocker
            elif not blocker:blocker='SETUP_INPUTS_UNAVAILABLE';blocker_code=blocker
            out.append({'setup':name,'direction':'CALL' if sign==1 else 'PUT','checks':checks,'blocker':blocker,'blocker_code':blocker_code,'trace_schema_version':2,'engine_version':VERSION,'at':now.astimezone(timezone.utc).isoformat(),'feed_quality':ctx.get('feed_quality','UNAVAILABLE'),'frames':{k:features.get(k,{}).get('trend','UNAVAILABLE') for k in ('1m','5m','15m','30m','1h','daily')},'opening_range':ctx.get('opening_range_status','UNAVAILABLE'),'continuity_synthetic_count':ctx.get('synthetic_continuity_minutes',0)})
    return out
def persist(path,traces,now):
    path.parent.mkdir(parents=True,exist_ok=True);db=sqlite3.connect(path,timeout=15);minute=now.replace(second=0,microsecond=0).astimezone(timezone.utc).isoformat()
    try:
        db.executescript('''CREATE TABLE IF NOT EXISTS rejection_traces(minute TEXT,setup TEXT,direction TEXT,version TEXT,snapshot_id TEXT,payload TEXT,evaluation_count INTEGER,PRIMARY KEY(minute,setup,direction,version));
        CREATE INDEX IF NOT EXISTS rejection_trace_time ON rejection_traces(minute);
        CREATE VIEW IF NOT EXISTS active_rejection_traces AS SELECT * FROM rejection_traces WHERE julianday(minute)>=julianday('now','-14 days');''')
        with db:
            for t in traces:
                body=json.dumps(t,sort_keys=True,allow_nan=False);sid=hashlib.sha256(body.encode()).hexdigest()[:24]
                db.execute('INSERT INTO rejection_traces VALUES(?,?,?,?,?,?,1) ON CONFLICT(minute,setup,direction,version) DO UPDATE SET payload=excluded.payload,snapshot_id=excluded.snapshot_id,evaluation_count=evaluation_count+1',(minute,t['setup'],t['direction'],t['engine_version'],sid,body))
    finally:db.close()
def summary(path,now):
    import collections
    from core.sessions import ET,market_session
    if not path.exists():return 'Rejection traces UNAVAILABLE (legacy session did not record them).'
    db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
    try:
        local=now.astimezone(ET);session=market_session(local.replace(hour=12,minute=0,second=0,microsecond=0))
        if not session['active']:return 'Why no ideas: no verified US regular session; historical traces remain retained.'
        beginning=local.replace(hour=9,minute=30,second=0,microsecond=0).astimezone(timezone.utc)
        ending=local.replace(hour=session['close_minute']//60,minute=session['close_minute']%60,second=0,microsecond=0).astimezone(timezone.utc)
        rows=db.execute('SELECT payload FROM rejection_traces WHERE minute>=? AND minute<? AND minute<=? ORDER BY minute DESC LIMIT 10000',(beginning.isoformat(),ending.isoformat(),now.astimezone(timezone.utc).isoformat())).fetchall();counts=collections.Counter();windows={}
        for row in rows:
            t=json.loads(row[0]);reasons=reason_codes(t);counts.update(reasons)
            for reason in reasons:windows.setdefault(reason,[]).append(stamp(t['at']).astimezone(ET).strftime('%H:%M'))
        return 'Why no ideas today (setup/minute aggregates; LEGACY_INFERRED is historical text grouping, not a stored predicate): '+('; '.join(k+' '+str(n)+' ('+min(windows[k])+'–'+max(windows[k])+' ET)' for k,n in counts.most_common(4)) or 'no failed traces recorded')
    except sqlite3.Error:return 'Rejection traces UNAVAILABLE.'
    finally:db.close()
