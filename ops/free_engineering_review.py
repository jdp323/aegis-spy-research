"""Prospective free-mode engineering evidence. Software is not trading edge."""
import json,math
from datetime import datetime,timezone,timedelta
from pathlib import Path
from core.sessions import ET,market_session

VERSION='free-mode-five-session-observation-v1'

def percentile(values,p):
    values=sorted(values)
    return values[max(0,math.ceil(len(values)*p)-1)] if values else None

def collect(day,root,now=None):
    now=now or datetime.now(timezone.utc);root=Path(root)
    opening=datetime.fromisoformat(day).replace(hour=9,minute=30,tzinfo=ET);session=market_session(opening)
    if not session['active']:return {'version':VERSION,'status':'NO_SESSION','date_et':day,'strategy_edge_proved':False}
    close=opening.replace(hour=session['close_minute']//60,minute=session['close_minute']%60)
    path=root/'logs/fast_path'/(day+'.jsonl');rows=[];malformed=0
    if path.exists():
        with path.open(encoding='utf-8') as f:
            for line in f:
                try:
                    row=json.loads(line);at=datetime.fromisoformat(row['at']);
                    if opening<=at<close:rows.append(row)
                except (ValueError,KeyError,TypeError):malformed+=1
    receipts=[]
    for minute in range(585,session['close_minute'],15):
        slot=opening.replace(hour=minute//60,minute=minute%60);receipt=root/'logs/notifications'/('v5-trend-'+day+'-'+str(minute)+'.json')
        record=json.loads(receipt.read_text()) if receipt.exists() else {}
        delay=None
        if record.get('accepted_at'):delay=(datetime.fromisoformat(record['accepted_at'].replace('Z','+00:00'))-slot).total_seconds()
        receipts.append({'slot_et':slot.isoformat(),'status':record.get('status','MISSING' if now>=close else 'PENDING_OR_NOT_OBSERVED'),'accepted_delay_seconds':delay})
    accepted=sum(r['status']=='TELEGRAM_ACCEPTED' for r in receipts);timely=sum(r['accepted_delay_seconds'] is not None and 0<=r['accepted_delay_seconds']<=30 for r in receipts)
    durations=[r['duration_seconds'] for r in rows if r.get('state')=='COMPLETED' and isinstance(r.get('duration_seconds'),(float,int))]
    quality=[r.get('result',{}).get('input_quality') or {} for r in rows if isinstance(r.get('result'),dict)]
    failures=sum(r.get('state') in ('FAILED_TICK','START_FAILED') for r in rows)
    db_failures=max((r.get('database',{}).get('failures',0) for r in rows),default=0)
    p95=percentile(durations,.95);after=now>=close+timedelta(minutes=20)
    targets={'all_expected_slots_accepted':accepted==len(receipts),'at_least_95pct_accepted_within30s':timely>=math.ceil(.95*len(receipts)),'local_fast_path_p95_under1s':p95 is not None and p95<1,'zero_unhandled_tick_failures':bool(rows) and failures==0 and malformed==0,'zero_observed_db_failures':bool(rows) and db_failures==0,'zero_orphan_duplicate_alerts':'UNVERIFIED_REQUIRES_RECEIPT_DEPENDENCY_AUDIT'}
    return {'version':VERSION,'date_et':day,'as_of':now.isoformat(),'status':'LIVE_SESSION_PENDING' if not after else 'FAIL' if any(v is False for v in targets.values()) else 'INCOMPLETE_VERIFICATION','targets':targets,'expected_slots':len(receipts),'accepted_slots':accepted,'timely_slots':timely,'slots':receipts,'completed_ticks':len(durations),'local_fast_path_p95_seconds':p95,'tick_failures':failures,'database_failure_counter_max':db_failures,'malformed_lines':malformed,'observed_trend_available_samples':sum(q.get('observed_trend_available') is True for q in quality),'strict_underlying_pass_samples':sum(q.get('strict_underlying_eligible') is True for q in quality),'quality_samples':len(quality),'phone_delivery_verified':False,'strategy_edge_proved':False,'option_performance':'NOT_MEASURED','limits':['Five complete genuine sessions are an initial engineering observation window, not evidence of edge.','Counters are process-local; restarts and absent logs must be reconciled separately.','Source/receipt intervals are not attributed solely to provider or network.','No PASS without independent orphan/duplicate and continuous-coverage verification.']}
