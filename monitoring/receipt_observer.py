"""Single-flight read-only receipt scans never block the market worker."""
import threading,time
from datetime import datetime,timezone

class ReceiptObserver:
    def __init__(self,root,scan=None,clock=time.monotonic,budget=15,interval=60):
        self.root=root;self.scan=scan;self.clock=clock;self.budget=budget;self.interval=interval;self.lock=threading.Lock();self.thread=None;self.running=False;self.closed=False;self.started=None;self.finished=None;self.day=None;self.value_day=None;self.rows=None;self.error=None;self.completed_at=None
    def _run(self,day):
        try:
            if self.scan is None:
                from ops.session_report import receipts
                rows=receipts(self.root,day,budget_seconds=self.budget)
            else:rows=self.scan(self.root,day)
            if not isinstance(rows,list):raise ValueError('INVALID_RECEIPT_SUMMARY')
            with self.lock:self.rows=rows;self.value_day=day;self.completed_at=datetime.now(timezone.utc).isoformat();self.error=None
        except Exception as error:
            with self.lock:self.error=type(error).__name__
        finally:
            with self.lock:self.running=False;self.finished=self.clock()
    def poll(self,day):
        with self.lock:
            now=self.clock()
            if not self.closed and not self.running and (self.day!=day or self.finished is None or now-self.finished>=self.interval):
                self.day=day;self.started=now;self.running=True;self.thread=threading.Thread(target=self._run,args=(day,),daemon=True,name='aegis-receipt-observer');self.thread.start()
            elapsed=now-self.started if self.running and self.started is not None else None
            age=now-self.finished if self.finished is not None else None
            available=self.value_day==day and self.rows is not None and age is not None and 0<=age<=120
            state='OVER_BUDGET' if self.running and elapsed>self.budget else 'FAILED' if self.error else 'REFRESHING' if self.running else 'CURRENT' if available else 'UNAVAILABLE'
            # Old-day, over-budget and failed observations never imply zero
            # uncertain deliveries. The caller skips aggregate warning decisions.
            usable=available and state in ('CURRENT','REFRESHING')
            health={'state':state,'at':datetime.now(timezone.utc).isoformat(),'day':day,'as_of':self.completed_at,'age_seconds':age,'elapsed_seconds':elapsed,'budget_seconds':self.budget,'error_type':self.error,'available':usable,'scope':'READ_ONLY_RECEIPT_METADATA; not phone delivery'}
            return list(self.rows) if usable else None,health
    def close(self):
        with self.lock:self.closed=True;thread=self.thread
        if thread:thread.join(timeout=.25)
