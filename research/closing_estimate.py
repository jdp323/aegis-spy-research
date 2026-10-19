"""Unvalidated public-bar closing-area baseline, never an options trade signal.

Target is the final regular5m bar close, not the exchange closing auction.
Historical remaining-session returns are matched by elapsed session time.
Chronological checks compare the median baseline to a no-change baseline.
"""
import json,math,hashlib,urllib.request,urllib.error
from datetime import datetime,timezone,timedelta
from core.storage import ROOT
from core.sessions import market_session,ET
from data.models import stamp
from data.public_spy import parse_chart

URL='https://query1.finance.yahoo.com/v8/finance/chart/SPY?interval=5m&range=60d&includePrePost=false'
VERSION='remaining-session-empirical-v1'
MIN_HISTORY=40

def refresh(now=None):
    """At most one public history attempt per ET date, including failures."""
    now=now or datetime.now(timezone.utc);target=ROOT/'research/closing_history.json'
    try:
        old=json.loads(target.read_text(encoding='utf-8'))
        if stamp(old['fetched_at']).astimezone(ET).date()==now.astimezone(ET).date():return old
    except (OSError,ValueError,KeyError,TypeError):pass
    result={'source':URL,'symbol':'SPY','fetched_at':now.isoformat(),'quality':'UNAVAILABLE','use':'DELAY_UNVERIFIED_RESEARCH_ONLY'}
    try:
        request=urllib.request.Request(URL,headers={'User-Agent':'AEGIS-local-research/1.0'})
        with urllib.request.urlopen(request,timeout=15) as response:body=response.read(8_000_000)
        bars=parse_chart(body);digest=hashlib.sha256(body).hexdigest();cache=ROOT/'data/closing_cache';cache.mkdir(exist_ok=True)
        (cache/(digest+'.json')).write_bytes(body);result.update(quality='PUBLIC_HISTORY',bars=bars,sha256=digest)
    except urllib.error.HTTPError as e:result.update(reason='HTTP_'+str(e.code))
    except Exception:result.update(reason='SOURCE_OR_SCHEMA_UNAVAILABLE')
    temp=target.with_suffix('.tmp');temp.write_text(json.dumps(result),encoding='utf-8');temp.replace(target)
    return result

def load(now=None):
    now=now or datetime.now(timezone.utc)
    try:
        d=json.loads((ROOT/'research/closing_history.json').read_text(encoding='utf-8'))
        if d.get('source')!=URL or d.get('symbol')!='SPY' or d.get('quality')!='PUBLIC_HISTORY':return None
        if not 0<=(now-stamp(d['fetched_at'])).total_seconds()<=86400:return None
        digest=d['sha256']
        if len(digest)!=64 or any(x not in '0123456789abcdef' for x in digest):return None
        body=(ROOT/'data/closing_cache'/(digest+'.json')).read_bytes()
        if hashlib.sha256(body).hexdigest()!=digest or parse_chart(body)!=d['bars']:return None
        return d
    except (OSError,ValueError,TypeError,KeyError):return None

def quantile(values,p):
    v=sorted(values);i=(len(v)-1)*p;lo=int(i);hi=min(lo+1,len(v)-1)
    return v[lo]+(v[hi]-v[lo])*(i-lo)

def estimate(observation,session,history=None,now=None):
    now=now or datetime.now(timezone.utc)
    out={'version':VERSION,'status':'UNAVAILABLE','action':'NO TRADE','validated':False,'target':'FINAL_REGULAR_5M_BAR_PROXY_NOT_OFFICIAL_AUCTION','reason':'INSUFFICIENT_VERIFIED_HISTORY'}
    if observation.get('quality')!='PUBLIC_RESEARCH_ONLY' or not session.get('active'):
        return {**out,'reason':'NO_FRESH_ACTIVE_SESSION_OBSERVATION'}
    # Displaying an estimate after its target has passed is never appropriate.
    bar=observation['bar'];local=bar.astimezone(ET);minute=local.hour*60+local.minute
    remaining=session['close_minute']-(minute+5)
    if remaining<10:return {**out,'reason':'SESSION_CLOSE_TOO_NEAR'}
    history=history if history is not None else load(now)
    if not history:return out
    if history.get('source')!=URL or history.get('symbol')!='SPY' or history.get('quality')!='PUBLIC_HISTORY':return {**out,'reason':'HISTORY_PROVENANCE_INVALID'}
    try:
        if not 0<=(now-stamp(history['fetched_at'])).total_seconds()<=86400:return {**out,'reason':'HISTORY_STALE'}
        groups={}
        for r in history['bars']:
            ts=r['timestamp']
            if type(ts) is not int:raise ValueError('INVALID_TIMESTAMP')
            t=datetime.fromtimestamp(ts,timezone.utc);local_t=t.astimezone(ET);day=local_t.date().isoformat();s=market_session(t)
            if not s['active'] or day>=session['date'] or ts%300:continue
            if any(type(r[k]) not in (int,float) or not math.isfinite(r[k]) for k in ('open','high','low','close','volume')):raise ValueError('INVALID_BAR')
            if not 0<r['low']<=min(r['open'],r['close'])<=max(r['open'],r['close'])<=r['high'] or r['volume']<=0:raise ValueError('INVALID_BAR')
            bucket=groups.setdefault(day,{})
            m=local_t.hour*60+local_t.minute
            if m in bucket:raise ValueError('DUPLICATE_BAR')
            bucket[m]=r
        examples=[]
        for day,rows in sorted(groups.items()):
            first=datetime.fromtimestamp(next(iter(rows.values()))['timestamp'],timezone.utc);s=market_session(first);end=s['close_minute']
            if s['early_close']!=session['early_close']:continue
            # Full contiguous sessions only. Same clock point means same horizon
            # when both the sample and current session have the same close.
            if any(m not in rows for m in range(570,end,5)) or minute not in rows:continue
            anchor=rows[minute]['close'];closing=rows[end-5]['close']
            examples.append({'day':day,'anchor':anchor,'closing':closing,'return':closing/anchor-1})
    except (ValueError,TypeError,KeyError,OverflowError):return {**out,'reason':'HISTORY_SCHEMA_INVALID'}
    if len(examples)<MIN_HISTORY:return {**out,'history_sessions':len(examples)}
    #30 earlier sessions train each chronological test, at least10 tests.
    errors=[];naive_errors=[];covered=[]
    for i in range(30,len(examples)):
        train=[r['return'] for r in examples[i-30:i]];x=examples[i]
        predicted=x['anchor']*(1+quantile(train,.5));low=x['anchor']*(1+quantile(train,.1));high=x['anchor']*(1+quantile(train,.9))
        errors.append(abs(predicted-x['closing']));naive_errors.append(abs(x['anchor']-x['closing']));covered.append(low<=x['closing']<=high)
    moves=[x['return'] for x in examples[-30:]];price=observation['levels']['last_close']
    bounds=[price*(1+quantile(moves,p)) for p in (.1,.5,.9)]
    if not all(math.isfinite(v) and v>0 for v in bounds):return {**out,'reason':'ESTIMATE_INVALID'}
    return {**out,'status':'EXPERIMENTAL_SCENARIOS','reason':'UNVALIDATED_PUBLIC_BAR_BASELINE','as_of_bar':bar.isoformat(),'low':round(bounds[0],2),'median':round(bounds[1],2),'high':round(bounds[2],2),'historical_sessions':len(moves),'remaining_minutes':remaining,'history_sha256':history.get('sha256'),'history_fetched_at':history['fetched_at'],'chronological_test_sessions':len(errors),'historical_mae_usd':sum(errors)/len(errors),'no_change_mae_usd':sum(naive_errors)/len(naive_errors),'beats_no_change':sum(errors)<sum(naive_errors),'historical_range_coverage':sum(covered)/len(covered),'limitations':'Empirical10th/50th/90th historical return quantiles. Not a calibrated confidence interval, current news forecast or options signal. Public delay and corporate-action adjustments unverified. Final5m proxy is not official closing auction.'}

if __name__=='__main__':
    d=refresh();print(json.dumps({k:v for k,v in d.items() if k!='bars'}));print('Bars:',len(d.get('bars',[])))
