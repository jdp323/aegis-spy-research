"""Read-only per-session acceptance accounting, every scheduled slot retained."""
import argparse,json,sqlite3,statistics,math
from pathlib import Path
from datetime import datetime,timedelta,timezone,date
from core.storage import ROOT
from core.sessions import ET,market_session
from data.models import stamp

def summarize(day,slots,receipts,evidence):
    local=datetime.combine(date.fromisoformat(day),datetime.min.time(),ET);s=market_session(local.replace(hour=12))
    expected=list(range(585,s['close_minute']-14,15)) if s['active'] else []
    rows=[]
    for minute in expected:
        ident='v5-trend-'+day+'-'+str(minute);scheduled=local+timedelta(minutes=minute);r=receipts.get(ident,{});e=evidence.get(ident,{})
        accepted=r.get('accepted_at');delay=(stamp(accepted)-scheduled).total_seconds() if accepted else None
        rows.append({'slot_et':scheduled.isoformat(),'reserved':ident in slots,'accepted':r.get('status')=='TELEGRAM_ACCEPTED','delay_seconds':delay,'within_30s':delay is not None and 0<=delay<=30,'underlying_gates_pass':e.get('underlying_gates_pass') is True,'risk_calendar_refusal_separate':e.get('calendar_refusal') is True,'missing_evidence':not bool(e)})
    delays=[];invalid=0
    for r in receipts.values():
        if r.get('alert_type')!='SPY_IDEA' or r.get('status')!='TELEGRAM_ACCEPTED':continue
        if not r.get('entry_revalidation',{}).get('checked_at'):invalid+=1
        if r.get('decision_at') and r.get('accepted_at'):
            delay=(stamp(r['accepted_at'])-stamp(r['decision_at'])).total_seconds()
            if delay>=0:delays.append(delay)
            else:invalid+=1
    ordered=sorted(delays);p95=ordered[math.ceil(.95*len(ordered))-1] if ordered else None
    passed=bool(rows) and sum(r['within_30s'] for r in rows)>=len(rows)-1 and sum(r['underlying_gates_pass'] for r in rows)>=len(rows)-1 and invalid==0
    return {'version':'master-session-targets-v1','day':day,'expected_slots':len(rows),'normal_day_target':'24/25 timing and underlying data; all25 denominator; risk-based WAIT separately classified','slots':rows,'on_time':sum(r['within_30s'] for r in rows),'underlying_pass':sum(r['underlying_gates_pass'] for r in rows),'entries':{'accepted_count':len(delays),'p50_seconds':statistics.median(delays) if delays else None,'p95_seconds':p95,'max_seconds':max(delays) if delays else None,'missing_or_invalid_revalidation':invalid,'latency_target':'p95 <=10 seconds; NO_SAMPLE does not pass'},'schedule_data_target_pass':passed,'three_session_status':'PENDING — individual report never substitutes for three consecutive future full sessions','live_signal_ready':False}

def collect(day,root=ROOT):
    root=Path(root);receipts={}
    for path in (root/'logs/notifications').glob('*.json'):
        try:
            r=json.loads(path.read_text());at=r.get('created_at')
            if at and stamp(at).astimezone(ET).date().isoformat()==day:receipts[r['id']]=r
        except (ValueError,OSError,KeyError):continue
    s=sqlite3.connect((root/'runtime/aegis.sqlite').resolve().as_uri()+'?mode=ro',uri=True,timeout=.25)
    try:slots={k.replace('v5-slot:TREND:','v5-trend-') for k, in s.execute("SELECT key FROM state WHERE key LIKE ?",('v5-slot:TREND:'+day+'-%',))}
    finally:s.close()
    evidence={};p=root/'runtime/observability.sqlite'
    if p.exists():
        from monitoring.trend_evidence import session_slots
        evidence=session_slots(p,day)
    return summarize(day,slots,receipts,evidence)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--date',required=True);p.add_argument('--output',required=True);a=p.parse_args();r=collect(a.date);Path(a.output).write_text(json.dumps(r,indent=2));print(json.dumps({k:r[k] for k in ('day','expected_slots','on_time','underlying_pass','three_session_status')}))
if __name__=='__main__':main()
