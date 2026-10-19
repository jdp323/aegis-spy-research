"""Read-only, allowlisted daily capture evidence; never invent closed-session data."""
import argparse,json,sqlite3,collections,hashlib
from datetime import datetime,timezone,timedelta,date
from core.storage import ROOT
from core.sessions import ET,market_session
from data.models import stamp

def ro(path):
    if not path.exists():return None
    return sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
def query(db,sql,args=()):
    if db is None:return []
    try:return db.execute(sql,args).fetchall()
    except sqlite3.OperationalError:return []
def count(rows):return dict(collections.Counter(rows))
def receipts(root,day):
    result=[]
    folder=root/'logs/notifications'
    confirmations=set();journal=folder/'owner_confirmations.jsonl'
    if journal.exists():
        for line in journal.read_text(encoding='utf-8').splitlines():
            try:
                entry=json.loads(line)
                if entry.get('status')=='CONFIRMED_BY_OWNER':confirmations.add(entry['receipt_hash'])
            except (ValueError,KeyError,TypeError):continue
    for p in folder.rglob('*.json') if folder.exists() else []:
        try:
            d=json.loads(p.read_text(encoding='utf-8'));at=stamp(d['created_at'])
            if at.astimezone(ET).date().isoformat()!=day:continue
            role='guest' if 'guests' in p.relative_to(folder).parts else 'owner';ident=hashlib.sha256(p.relative_to(folder).as_posix().encode()+b'\0'+p.read_bytes()).hexdigest();status='CONFIRMED_BY_OWNER' if role=='owner' and ident in confirmations else d.get('status','PENDING_OR_UNCERTAIN')
            result.append({'role':role,'kind':d.get('kind','UNKNOWN'),'status':status,'failure_class':d.get('failure_class','UNAVAILABLE'),'age_seconds':(datetime.now(timezone.utc)-at).total_seconds()})
        except (OSError,ValueError,KeyError,TypeError):continue
    return result
def collect(day,root=ROOT,now=None):
    root=type(ROOT)(root);now=now or datetime.now(timezone.utc);d=date.fromisoformat(day);noon=datetime(d.year,d.month,d.day,12,tzinfo=ET);session=market_session(noon)
    result={'schema_version':1,'date_et':day,'generated_at_utc':now.isoformat(),'scope':'Read-only allowlisted session evidence. No private identifiers. No strategy validation.','LIVE_SIGNAL_READY':False}
    if not session['active']:
        return {**result,'status':'NO_SESSION','reasons':[session['state']]}
    opening=noon.replace(hour=9,minute=30);closing=noon.replace(hour=session['close_minute']//60,minute=session['close_minute']%60)
    expected={int((opening+timedelta(minutes=i)).timestamp()) for i in range(session['close_minute']-570)}
    recorded=set();backfilled=set();stream_origin=set();backfilled_after=set();confirmed=set();feed='IEX';a=ro(root/'runtime/aegis.sqlite');h=ro(root/'runtime/history.sqlite');o=ro(root/'runtime/observability.sqlite');ideas=ro(root/'runtime/ideas.sqlite')
    def state(key):
        rows=query(a,'SELECT payload FROM state WHERE key=?',(key,));return json.loads(rows[0][0]) if rows else None
    try:
        # Never sum two feeds into an apparently complete tape.
        for source,payload,captured_at in query(h,'SELECT source_timestamp,payload,recorded_at FROM session_bars WHERE feed_quality=?',(feed,)):
            t=int(stamp(source).timestamp())
            if t in expected:
                recorded.add(t)
                if json.loads(payload).get('source')=='REST_BACKFILL':
                    backfilled.add(t)
                    if stamp(captured_at)>=closing:backfilled_after.add(t)
                else:stream_origin.add(t)
        for r in state('research_stream_bars:SPY:iex') or []:
            t=int(stamp(r['t']).timestamp())
            if t in expected:
                recorded.add(t)
                if r.get('source')=='REST_BACKFILL':backfilled.add(t)
                else:stream_origin.add(t)
        for t, in query(o,'SELECT timestamp FROM bar_confirmations WHERE feed=?',('iex',)):
            ts=int(stamp(t).timestamp())
            if ts in expected and ts not in recorded:confirmed.add(ts)
        hours=[]
        for hour in sorted({datetime.fromtimestamp(t,timezone.utc).astimezone(ET).hour for t in expected}):
            bucket={t for t in expected if datetime.fromtimestamp(t,timezone.utc).astimezone(ET).hour==hour}
            hours.append({'hour_et':f'{hour:02d}:00','expected':len(bucket),'recorded':len(bucket&recorded),'backfilled':len(bucket&backfilled),'NO_PRINT_CONFIRMED':len(bucket&confirmed),'missing':len(bucket-recorded-confirmed)})
        events=[]
        for at,feed_,kind,payload in query(o,'SELECT at,feed,event,payload FROM stream_events ORDER BY at'):
            if stamp(at).astimezone(ET).date().isoformat()==day:events.append((at,feed_,kind,json.loads(payload)))
        outages=[];missing=sorted(expected-recorded-confirmed)
        for t in missing:
            if outages and t==outages[-1]['last_epoch']+60:outages[-1]['last_epoch']=t;outages[-1]['missing_minutes']+=1
            else:outages.append({'first_epoch':t,'last_epoch':t,'missing_minutes':1})
        for interval in outages:
            begin=interval.pop('first_epoch');end=interval.pop('last_epoch')+60
            causes=[e[2]+':'+e[3].get('reason','UNAVAILABLE') for e in events if e[1] in ('iex','supervisor','worker') and begin-300<=stamp(e[0]).timestamp()<=end and e[2] in ('DISCONNECT','PERMISSION_ERROR','WATCHDOG_RECONNECT','WATCHDOG_RESTART','PROCESS_PAUSED')]
            interval.update(start_et=datetime.fromtimestamp(begin,timezone.utc).astimezone(ET).isoformat(),end_et=datetime.fromtimestamp(end,timezone.utc).astimezone(ET).isoformat(),logged_causes=sorted(set(causes)) or ['UNKNOWN'])
        messages=[]
        for p in (root/'monitoring/outbox').glob('*.json'):
            try:
                obj=json.loads(p.read_text());typ=obj.get('alert_type')
                if typ not in ('PREOPEN','TREND_LINE','SPY_IDEA','IDEA_UPDATE','RECAP'):continue
                when=stamp(obj.get('created_at') or obj.get('timestamp') or obj['expires_at'])
                if when.astimezone(ET).date().isoformat()!=day:continue
                text=obj.get('text','');messages.append({'type':typ,'valid':typ=='TREND_LINE' and ('Price bias:' in text or 'Trend: ' in text),'stale':typ=='TREND_LINE' and ('Trend unavailable:' in text or 'data not fresh' in text or 'history missing' in text)})
            except (OSError,ValueError,KeyError,TypeError):continue
        # Scheduled reservations survive dispatch removing/archiving outbox files.
        reservations=query(a,"SELECT key,payload FROM state WHERE key LIKE 'v5-slot:%'")
        traces=[];outside_session_trace_count=0
        day_start=noon.replace(hour=0,minute=0,second=0,microsecond=0)
        day_end=day_start+timedelta(days=1)
        for at,payload in query(o,'SELECT minute,payload FROM rejection_traces WHERE minute>=? AND minute<? ORDER BY minute', (day_start.astimezone(timezone.utc).isoformat(),day_end.astimezone(timezone.utc).isoformat())):
            moment=stamp(at)
            if moment.astimezone(ET).date().isoformat()==day:
                if opening<=moment<closing:traces.append(json.loads(payload))
                else:outside_session_trace_count+=1
        failed=count(check for tr in traces for check,value in tr.get('checks',{}).items() if value.get('state')=='FAIL')
        by_window={};frame_windows={}
        from core.rejection_trace import reason_codes
        for tr in traces:
            hour=stamp(tr['at']).astimezone(ET).strftime('%H:00 ET');window=by_window.setdefault(hour,collections.Counter());window.update(reason_codes(tr))
            frames=frame_windows.setdefault(hour,{k:collections.Counter() for k in ('1m','5m','15m','30m','1h','daily')})
            for k,v in tr.get('frames',{}).items():
                if k in frames:frames[k].update(['available' if v not in (None,'UNAVAILABLE') else 'unavailable'])
        backfill_rows=[r for r in query(o,'SELECT feed,fetched_at,status,bar_count,confirmed_count,reason FROM backfill_runs') if stamp(r[1]).astimezone(ET).date().isoformat()==day]
        predicate_counts=count(e[3].get('predicate','UNKNOWN') for e in events if e[2]=='DATA_REJECTION')
        trend_records=[json.loads(payload) for at,payload in query(o,'SELECT at,payload FROM trend_status_events ORDER BY at') if stamp(at).astimezone(ET).date().isoformat()==day]
        if trend_records:
            messages=[m for m in messages if m['type']!='TREND_LINE']+[{'type':'TREND_LINE','valid':r['status']=='VALID_UNDERLYING','stale':r['status']!='VALID_UNDERLYING'} for r in trend_records]
            predicate_counts=count(r.get('predicate') or 'PASS' for r in trend_records)
        closed=[];generated=set()
        for payload, in query(ideas,'SELECT payload FROM idea_events ORDER BY rowid'):
            p=json.loads(payload)
            if stamp(p['timestamp']).astimezone(ET).date().isoformat()==day:generated.add(p['signal_id'])
            if p.get('closed_at') and stamp(p['closed_at']).astimezone(ET).date().isoformat()==day:closed.append(p)
        closed={p['signal_id']:p for p in closed}
        source_rate=len(recorded|confirmed)/len(expected)
        expected_trends=(session['close_minute']-585)//15
        actual_trends=sum(m['type']=='TREND_LINE' for m in messages)
        after=now>=closing
        reasons=[]
        if not after:reasons.append('Session incomplete; this is a partial report')
        if source_rate<.95:reasons.append('Recorded/confirmed regular-session minute coverage below 95%')
        if actual_trends!=expected_trends:reasons.append('Every scheduled trend status not established from retained outbox evidence')
        clock=state('ntp_clock') or {}
        config=json.loads((root/'config/upgrade.json').read_text())
        result.update(status='PASS' if not reasons else 'FAIL' if after and source_rate<.95 else 'WARN',reasons=reasons or ['At least 95% coverage and all scheduled trend statuses recorded'],feed_quality=feed,minute_coverage=hours,outages=outages,recorded_fraction=source_rate,messages={'by_type':count(m['type'] for m in messages),'trend_valid':sum(m['valid'] for m in messages),'trend_stale':sum(m['stale'] for m in messages),'expected_trend_slots':expected_trends,'failed_predicates':predicate_counts,'receipt_statuses':count(r['status'] for r in receipts(root,day)),'receipt_by_role_and_kind':count(r['role']+':'+r['kind']+':'+r['status'] for r in receipts(root,day)),'delivery_note':'Outbox counts are queued/reserved, not phone-delivery proof; definitive acceptance is recorded separately.'},idea_engine={'generated':len(generated),'closed':len(closed),'outcomes':count(p.get('exit_reason','UNAVAILABLE') for p in closed.values()),'top_failed_checks':failed,'trace_count':len(traces),'rejection_reasons_by_hour':{h:dict(c) for h,c in by_window.items()}},frames={'by_hour':{h:{k:dict(v) for k,v in fs.items()} for h,fs in frame_windows.items()},'session_availability':'Recorded per evaluation in rejection traces; missing historical traces cannot be reconstructed'},opening_range={'recorded':len({int((opening+timedelta(minutes=i)).timestamp()) for i in range(15)}&recorded),'status':'AVAILABLE' if all(int((opening+timedelta(minutes=i)).timestamp()) in recorded for i in range(15)) else 'OPENING RANGE UNAVAILABLE'},clock_stream={'ntp_offset_seconds':clock.get('offset_seconds'),'skew_tolerance_seconds':config.get('max_future_skew_seconds'),'events_by_type':count(e[2] for e in events),'backfill_runs':len(backfill_rows),'backfill_statuses':count(r[2] for r in backfill_rows),'backfill_errors':count(r[5] for r in backfill_rows if r[5]),'reconnect_count':sum(e[2]=='RECONNECT' for e in events),'pauses_detected':sum(e[2]=='PROCESS_PAUSED' for e in events)},limitations=['Legacy notifier reservations do not prove handset receipt.','Legacy outbox retention may not establish every message slot.','Confirmed absence concerns this feed eligible bars only; it does not establish total-market absence.','Clock observation is latest available, not a fabricated session time series.'])
        retained_gaps=[]
        for t in sorted(expected-stream_origin):
            if retained_gaps and t==retained_gaps[-1]['last']+60:retained_gaps[-1]['last']=t;retained_gaps[-1]['minutes']+=1
            else:retained_gaps.append({'first':t,'last':t,'minutes':1})
        for gap in retained_gaps:
            first=gap.pop('first');last=gap.pop('last')+60
            gap.update(start_et=datetime.fromtimestamp(first,timezone.utc).astimezone(ET).isoformat(),end_et=datetime.fromtimestamp(last,timezone.utc).astimezone(ET).isoformat(),logged_causes=sorted(set(e[2]+':'+e[3].get('reason','UNAVAILABLE') for e in events if first-300<=stamp(e[0]).timestamp()<=last and e[1] in ('iex','worker','supervisor') and e[2] in ('DISCONNECT','PROCESS_PAUSED','PERMISSION_ERROR','WATCHDOG_RECONNECT','WATCHDOG_RESTART'))) or ['UNKNOWN'])
        result['retained_stream_gap_intervals']=retained_gaps
        result['backfill_timing']={'genuine_rest_minutes_recorded_after_close':len(backfilled_after-stream_origin),'note':'Coverage is as of generation. A retrospective REST repair cannot prove real-time availability at a Friday decision or restore Friday setup traces.'}
        result['opening_range']['scope']='As-of report-generation coverage; does not prove availability at 09:45 on the historical session.'
        result['messages']['scheduled_analysis_statuses']=count(r['status'] for r in trend_records)
        result['messages']['status_evidence']='Append-only composed trend status records when present; legacy outbox wording otherwise. Neither establishes phone delivery.'
        result['idea_engine']['outside_regular_session_trace_rows']=outside_session_trace_count
        result['idea_engine']['rejection_summary_scope']='Regular session [open, close), counted per retained setup/direction/minute trace. Raw pre/post-session traces remain in the ledger; outside-session rows are counted separately.'
        result['idea_engine']['rejection_reason_labels']='Unprefixed codes were explicitly recorded. LEGACY_STORED codes were constant blocker values; LEGACY_INFERRED codes are exact-prefix text groupings, not recovered predicates; LEGACY_UNKNOWN means no supported classification. Raw trace text/measurements remain unchanged.'
        return result
    finally:
        for db in (a,h,o,ideas):
            if db:db.close()
def write(day,root=ROOT,now=None):
    from ops.verification_packet import scan,redact_deep
    result=collect(day,root,now);raw=json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)
    if scan(raw):raise ValueError('SESSION_REPORT_SECRET_REJECTED')
    raw=json.dumps(redact_deep(result),indent=2,ensure_ascii=False,allow_nan=False)
    md='# AEGIS session report — '+day+'\n\nVERIFIED: retained read-only evidence as of generation. Missing evidence is unavailable. No profitability or strategy validation claimed.\n\n```json\n'+raw+'\n```\n'
    if len(md.encode())>60000:raise ValueError('SESSION_REPORT_TOO_LARGE')
    folder=root/'daily_reports';folder.mkdir(parents=True,exist_ok=True);base=folder/('SESSION_REPORT_'+day)
    # Stable requested deliverable, prior versions preserved if content changed.
    for suffix,body in (('.json',raw),('.md',md)):
        p=base.with_suffix(suffix)
        if p.exists() and p.read_text(encoding='utf-8')!=body:
            archive=folder/'session_report_archive';archive.mkdir(exist_ok=True);(archive/(p.stem+'_'+hashlib.sha256(p.read_bytes()).hexdigest()[:12]+suffix)).write_bytes(p.read_bytes())
        tmp=p.with_suffix(suffix+'.pending');tmp.write_text(body,encoding='utf-8');tmp.replace(p)
    return base.with_suffix('.md')
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--date',default=datetime.now(timezone.utc).astimezone(ET).date().isoformat());args=parser.parse_args();print(write(args.date))
if __name__=='__main__':main()
