"""Bounded prospective IEX BBO writer; disk work stays off stream ingestion.

These are underlying research quotes, never option quotes or a consolidated
tape. Drops/failed writes are counted; missing history is not reconstructed.
"""
import json,queue,threading
from datetime import datetime,timezone
from pathlib import Path
from data.models import finite,stamp
from core.sessions import ET

VERSION='iex-prospective-bbo-v1'

class QuoteRecorder:
    def __init__(self,root,maximum=4096):
        self.root=Path(root);self.queue=queue.Queue(maximum);self.stop=threading.Event();self.dropped=0;self.failures=0;self.written=0
        self.thread=threading.Thread(target=self._run,name='aegis-iex-quote-writer',daemon=True);self.thread.start()
    def offer(self,quote):
        from core.isolation import assert_real
        assert_real(quote)
        p=quote.get('payload') or {}
        if quote.get('provider')!='alpaca-iex' or quote.get('symbol')!='SPY' or not finite(p.get('bid')) or not finite(p.get('ask')) or not 0<p['bid']<=p['ask']:return False
        source=stamp(quote['source_timestamp']);received=stamp(quote['received_timestamp'])
        row={'version':VERSION,'symbol':'SPY','provider':'alpaca-iex','feed':'IEX','source_at':source.isoformat(),'received_at':received.isoformat(),'bid':p['bid'],'ask':p['ask'],'entitlement':'SINGLE_EXCHANGE_RESEARCH_ONLY','option_quote':False}
        try:self.queue.put_nowait(row);return True
        except queue.Full:self.dropped+=1;return False
    def _run(self):
        while not self.stop.is_set() or not self.queue.empty():
            try:row=self.queue.get(timeout=.2)
            except queue.Empty:continue
            try:
                day=stamp(row['received_at']).astimezone(ET).date().isoformat();folder=self.root/'logs/market_capture'/day;folder.mkdir(parents=True,exist_ok=True)
                row['persisted_at']=datetime.now(timezone.utc).isoformat()
                with (folder/'iex_bbo.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(row,allow_nan=False)+'\n')
                self.written+=1
            except (OSError,ValueError):self.failures+=1
            finally:self.queue.task_done()
    def health(self):return {'version':VERSION,'written':self.written,'dropped_queue_full':self.dropped,'write_failures':self.failures,'pending':self.queue.qsize(),'thread_alive':self.thread.is_alive(),'basis':'Prospective raw IEX BBO; not option or consolidated prices; no history completeness claim.'}
    def close(self,timeout=1):
        self.stop.set();self.thread.join(timeout);return self.health()
