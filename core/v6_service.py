"""Owner-only outage warnings, pre-open check and session-report scheduling."""
from datetime import datetime,timezone,timedelta
from core.storage import ROOT
from core.sessions import ET,market_session
from data.reliability import Events,PauseProbe,active,watchdog_age

class Reliability:
    def __init__(self,store,provider,root=ROOT,clock=None,background=False):
        from data.backfill import Backfill,BackgroundBackfill
        self.clock=clock or (lambda:datetime.now(timezone.utc));self.root=root;self.store=store;self.events=Events(root/'runtime/observability.sqlite');self.probe=PauseProbe();self.started=self.clock()
        self.backfill=BackgroundBackfill(root/'runtime/observability.sqlite',store.path,provider) if background else Backfill(root/'runtime/observability.sqlite',provider)
    def close(self):
        self.backfill.close();self.events.close()
    def tick(self,now,enqueue):
        pause=self.probe.check(now)
        if pause:self.events.add('PROCESS_PAUSED','worker',now,**pause)
        self.backfill.tick(self.store,now)
        if hasattr(self.backfill,'health'):self.store.put('history_worker_health',self.backfill.health())
        # Clock after all blocking reads/network work. Backfill is not a live message.
        now=self.clock();local=now.astimezone(ET);day=local.date().isoformat()
        if active(now):
            age=watchdog_age(self.store.get('last_market:iex') or {},now,self.started)
            health=self.store.get('stream:iex') or {};key='v6-outage:'+day;outage=self.store.get(key)
            if age>=90 and not outage:
                recent=self.events.db.execute("SELECT event,payload FROM stream_events WHERE feed IN ('iex','worker','supervisor') AND at>=? AND event IN ('DISCONNECT','PERMISSION_ERROR','PROCESS_PAUSED') ORDER BY at DESC LIMIT 1",((now-timedelta(minutes=5)).isoformat(),)).fetchone()
                import json
                cause=(recent[0]+':'+json.loads(recent[1]).get('reason','SCHEDULING_GAP') if recent else None) or health.get('error_type') or ('NO_VALID_MARKET_MESSAGES' if health.get('state') in ('CONNECTED','CONNECTED_IDLE') else health.get('state','UNKNOWN'))
                ident='v6-outage-'+day+'-'+str(int(now.timestamp()))
                self.store.put(key,{'id':ident,'at':now.isoformat(),'reason':cause})
                enqueue(self.store,ident,'DATA WARNING — IEX has no valid market messages for '+str(int(age))+' seconds. Cause: '+cause+'. Watchdog recovery is active. No fresh-data idea is issued.','PRIVATE','owner',kind='RESEARCH',alert_type='DATA_WARNING')
            elif 0<=age<15 and outage:
                enqueue(self.store,outage['id']+'-recovered','DATA RECOVERY — fresh IEX market messages resumed. Bar continuity and history are checked separately.','PRIVATE','owner',kind='RESEARCH',alert_type='DATA_RECOVERY');self.store.put(key,None)
            if local.hour*60+local.minute>=560 and local.hour*60+local.minute<565 and not self.store.get('v6-precheck:'+day):
                from data.reliability import quote_diagnostics,describe
                from data.models import stamp
                q=self.store.get('research_quote:SPY:iex') or {};diagnostic=quote_diagnostics(q,now,'alpaca-iex');reason=describe(diagnostic) if diagnostic['predicate'] else None
                if not reason and health.get('state') not in ('CONNECTED','CONNECTED_IDLE'):reason='Stream not connected: '+str(health.get('state','UNAVAILABLE'))
                if not reason:
                    try:
                        heartbeat_age=(now-stamp(health['at'])).total_seconds()
                        if not 0<=heartbeat_age<=30:reason='Heartbeat age outside 0–30 seconds: '+str(round(heartbeat_age,3))+' s'
                    except (KeyError,ValueError):reason='Heartbeat timestamp unavailable'
                bar=self.store.get('research_stream_bar:SPY:iex') or {}
                try:
                    bar_age=(now-stamp(bar['source_timestamp'])).total_seconds()-60
                    if not reason and not 0<=bar_age<=120:reason='Premarket bar end age outside 0–120 seconds: '+str(round(bar_age,3))+' s'
                except (KeyError,ValueError):
                    if not reason:reason='Premarket stream bar unavailable; quotes alone do not prove bar capture'
                self.store.put('v6-precheck:'+day,{'at':now.isoformat(),'reason':reason})
                self.events.add('PREOPEN_CHECK','worker',now,state='WARN' if reason else 'PASS')
                if reason:enqueue(self.store,'v6-precheck-'+day,'DATA WARNING — 09:20 ET stream self-check: '+reason+'. Next regular trend line: 09:45 ET.','PRIVATE','owner',kind='RESEARCH',alert_type='DATA_WARNING')
        from ops.session_report import receipts
        receipt_rows=receipts(self.root,day)
        problems=sum(r['status'] in ('PENDING_OR_UNCERTAIN','UNCERTAIN_AFTER_SEND','FAILED_NOT_ACCEPTED') for r in receipt_rows)
        if problems>2 and not self.store.get('v6-delivery-warning:'+day):
            self.store.put('v6-delivery-warning:'+day,{'at':now.isoformat(),'count':problems})
            enqueue(self.store,'v6-delivery-warning-'+day,'SYSTEM WARNING — '+str(problems)+' session delivery receipts failed or are uncertain. Review python -m ops.receipts. Uncertain sends are not automatically retried.','PRIVATE','owner',kind='RESEARCH',alert_type='SYSTEM_WARNING')
        noon=local.replace(hour=12,minute=0,second=0,microsecond=0);session=market_session(noon)
        report_minute=session['close_minute']+20
        if session['active'] and report_minute<=local.hour*60+local.minute<report_minute+5 and not self.store.get('v6-session-report:'+day):
            from ops.session_report import write
            write(day,self.root);self.store.put('v6-session-report:'+day,{'at':now.isoformat()})
