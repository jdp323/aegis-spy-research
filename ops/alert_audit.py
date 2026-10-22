"""Read-only retrospective alert audit. Minute-open proxies are not executable fills."""
import argparse,json,sqlite3,hashlib,math
from pathlib import Path
from datetime import datetime,timezone,timedelta
from collections import Counter
from data.models import stamp
from core.sessions import ET
from features.indicators import normalize,resample,calculate

STOP_TRIALS=('ORIGINAL','STRUCTURE_3X5M_ATR_BUFFER','ATR5M_1','ATR5M_1.5','ATR5M_2')
DELAYS=(15,30,60)

def path_outcome(bars,entry,stop,target,sign,end):
    for b in bars:
        if b['timestamp']>=end.timestamp():break
        s=b['low']<=stop if sign==1 else b['high']>=stop
        t=b['high']>=target if sign==1 else b['low']<=target
        if s or t:return {'result':'AMBIGUOUS_STOP_TARGET' if s and t else 'INVALIDATION' if s else 'TARGET','bar_end':datetime.fromtimestamp(b['timestamp']+60,timezone.utc).isoformat()}
    return {'result':'TIME_EXIT' if bars and bars[-1]['timestamp']+60>=end.timestamp() else 'MISSING_OUTCOME','bar_end':None}

def audit(ideas,bars,receipts):
    results=[]
    for i in sorted(ideas,key=lambda r:r['timestamp']):
        issued=stamp(i['timestamp']);sign=1 if i['direction']=='CALL' else -1
        # Recover the exact completed candle from the immutable signal identity.
        match=[]
        for b in bars:
            if not 0<=issued.timestamp()-b['timestamp']-60<=120:continue
            identity=['spy-ideas-v3-entry-window',i['setup_type'],i['direction'],bool(i.get('early')),b['timestamp'],round(i['trigger'],4)]
            if hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:24]==i['signal_id']:match.append(b)
        confirmed=datetime.fromtimestamp(match[0]['timestamp']+60,timezone.utc) if len(match)==1 else None
        accepted=receipts.get(i.get('idea_event_id'));at=stamp(accepted) if accepted else None
        row={k:i.get(k) for k in ('signal_id','direction','setup_type','timestamp','trigger_level','reference_midpoint','modeled_entry_fill','invalidation','t1','t2','risk_distance','max_hold_until','signal_expiry','exit_reason','closed_at','t1_hit','coverage_status')}
        row.update(confirmation_at=confirmed.isoformat() if confirmed else None,confirmation_basis='IMMUTABLE_SIGNAL_ID_MATCH' if confirmed else 'UNAVAILABLE',telegram_accepted_at=accepted,acceptance_delay_seconds=(at-issued).total_seconds() if at else None,first_achievable_entry='UNAVAILABLE_NO_EXECUTABLE_QUOTE_TRADE_HISTORY',overlapping_original_ids=[x['signal_id'] for x in ideas if x['signal_id']!=i['signal_id'] and stamp(x.get('opened_at',x['timestamp']))<stamp(i.get('closed_at',i['max_hold_until'])) and issued<stamp(x.get('closed_at',x['max_hold_until']))],trials=[])
        after=[b for b in bars if b['timestamp']>=stamp(i.get('opened_at',i['timestamp'])).timestamp() and b['timestamp']<stamp(i['max_hold_until']).timestamp()]
        row['first_touch']={}
        for label,level in [('invalidation',i['invalidation']),('target1',i['t1']),('target2',i['t2'])]:
            touch=next((b for b in after if (b['low']<=level if sign==1 else b['high']>=level) if label=='invalidation'),None) if label=='invalidation' else next((b for b in after if (b['high']>=level if sign==1 else b['low']<=level)),None)
            row['first_touch'][label]=datetime.fromtimestamp(touch['timestamp']+60,timezone.utc).isoformat() if touch else None
        prior=[b for b in bars if b['timestamp']+60<=issued.timestamp()];five=resample(prior,5);atr=calculate(five).get('atr14');struct=(min(b['low'] for b in five[-3:]) if sign==1 else max(b['high'] for b in five[-3:])) if len(five)>=3 else None
        stops={'ORIGINAL':i['invalidation'],'STRUCTURE_3X5M_ATR_BUFFER':struct-sign*.10*atr if struct is not None and atr else None,**{'ATR5M_'+str(x):i['reference_midpoint']-sign*x*atr if atr else None for x in (1,1.5,2)}}
        for delay in DELAYS:
            eligible=at+timedelta(seconds=delay) if at else None
            start=math.ceil(eligible.timestamp()/60)*60 if eligible else None
            b=next((b for b in bars if b['timestamp']==start),None)
            for variant in STOP_TRIALS:
                t={'delay_seconds':delay,'stop_variant':variant,'population':'DEVELOPMENT_STOP_ONLY_FIXED_ORIGINAL_TARGETS','entry_proxy_at':datetime.fromtimestamp(start,timezone.utc).isoformat() if start else None,'entry_proxy_price':b['open'] if b else None,'stop':stops[variant]}
                if not b or not eligible:t['result']='MISSING_ENTRY_PROXY'
                elif start>=min(stamp(i['signal_expiry']).timestamp(),stamp(i['max_hold_until']).timestamp()):t['result']='ENTRY_EXPIRED'
                elif (b['open']-i['do_not_chase'])*sign>0:t['result']='CHASE_LIMIT_REJECTED'
                elif stops[variant] is None:t['result']='MISSING_STOP_INPUT'
                elif (b['open']-stops[variant])*sign<=0:t['result']='ALREADY_INVALIDATED'
                else:t.update(path_outcome([x for x in bars if x['timestamp']>=start],b['open'],stops[variant],i['t2'],sign,stamp(i['max_hold_until'])))
                row['trials'].append(t)
        results.append(row)
    end=None;kept=[];suppressed=[]
    for r in results:
        if end and stamp(r['timestamp'])<end:suppressed.append(r['signal_id']);continue
        kept.append(r['signal_id']);end=stamp(r.get('closed_at') or r['max_hold_until'])
    return {'scope':'RETROSPECTIVE DEVELOPMENT ONLY; historical outcomes unchanged','alerts':results,'reported_research_outcomes':dict(Counter(i.get('exit_reason') for i in ideas)),'primary_policy_replay':{'kept':kept,'suppressed_overlap':suppressed,'meaning':'Same historical detection clocks and terminal times, not a new profitability backtest.'},'trial_counts':{'stop_variants':5,'human_delays':3,'total_per_alert':15},'limits':['Telegram acceptance is not phone delivery.','No underlying executable quote/trade archive at every notification; first achievable fills unavailable.','Minute opens are delayed research proxies; no limit-fill assumption.','Same-minute stop/target ordering is ambiguous.','Alternative stops are frozen sensitivity tests, not selected production parameters.','No genuine option outcomes or actual personal fills inferred.']}

def load(root,day):
    root=Path(root).resolve()
    def ro(p):return sqlite3.connect(p.as_uri()+'?mode=ro',uri=True,timeout=2)
    db=ro(root/'runtime/ideas.sqlite');rows={r['signal_id']:r for r in (json.loads(v[0]) for v in db.execute('SELECT payload FROM idea_events ORDER BY rowid'))};db.close()
    ideas=[r for r in rows.values() if r.get('alerted') and stamp(r['timestamp']).astimezone(ET).date().isoformat()==day]
    db=ro(root/'runtime/aegis.sqlite');v=db.execute("SELECT payload FROM state WHERE key='research_stream_bars:SPY:iex'").fetchone();db.close()
    bars=normalize(json.loads(v[0]) if v else [],now=datetime.now(timezone.utc));receipts={}
    for p in (root/'logs/notifications').glob('*.json'):
        try:r=json.loads(p.read_text(encoding='utf-8'))
        except (ValueError,OSError):continue
        if r.get('recipient_role')=='owner' and r.get('status')=='TELEGRAM_ACCEPTED' and r.get('accepted_at'):receipts[r.get('id',p.stem)]=r['accepted_at']
    result=audit(ideas,bars,receipts);result['source_bars_sha256']=hashlib.sha256(json.dumps(bars,sort_keys=True).encode()).hexdigest();return result
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True);p.add_argument('--day',required=True);p.add_argument('--output',required=True);a=p.parse_args();r=load(a.root,a.day);Path(a.output).write_text(json.dumps(r,indent=2));print(json.dumps({'alerts':len(r['alerts']),'outcomes':r['reported_research_outcomes'],'confirmation_matches':sum(x['confirmation_at'] is not None for x in r['alerts']),'accepted':sum(x['telegram_accepted_at'] is not None for x in r['alerts']),'primary_replay':r['primary_policy_replay']},indent=2))
