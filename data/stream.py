"""Read-only SIP/OPRA streams, bounded reconnects, no broker endpoints."""
import asyncio,json,os,random,sys,time,signal,sqlite3
from pathlib import Path
from datetime import datetime,timezone
from core.storage import Store,ROOT,iso
from data.models import quote,Datum,Quality,finite,stamp
from data.reliability import Events,PauseProbe,active,connection_watchdog_age
sys.path.insert(0,str(ROOT/'.vendor'))
def decode(raw,options=False):
    if options:
        import msgpack
        return msgpack.unpackb(raw,raw=False)
    return json.loads(raw)
def encode(payload,options=False):
    if options:
        import msgpack
        return msgpack.packb(payload,use_bin_type=True)
    return json.dumps(payload)
class Stream:
    def __init__(self,store,options=False,connect=None,feed='sip',max_future_skew_seconds=0):
        if type(max_future_skew_seconds) not in (int,float) or not 0<=max_future_skew_seconds<=5:raise ValueError('INVALID_SKEW_BUDGET')
        self.max_future_skew_seconds=max_future_skew_seconds
        if feed not in ('sip','iex') or (options and feed!='sip'):raise ValueError('UNSUPPORTED_FEED')
        self.store=store;self.options=options;self.name='opra' if options else feed;self.connect=connect;self.stop=asyncio.Event();self.attempt=0;self.last_source={};self.clock_rejected_count=0;self.next_clock_record=0
        self.event_path=store.path.with_name('observability.sqlite') if getattr(store,'path',None) is not None else None
        self.probe=PauseProbe();self.first=False;self.minute=None;self.message_count=0;self.connection_id=None;self.started=datetime.now(timezone.utc)
    def log(self,event,**fields):
        if self.event_path:
            try:
                if not hasattr(self,'_events'):
                    self._events=Events(self.event_path);self._events.db.execute('PRAGMA busy_timeout=250')
                    self.store._closers.append(self._events.close)
                    # Close alongside the owning Store (also isolated fixtures).
                    self.store.db.execute('PRAGMA busy_timeout=500')
                self._events.add(event,self.name,**fields)
            except sqlite3.OperationalError:
                self.telemetry_failures=getattr(self,'telemetry_failures',0)+1
    def record_provider_rejections(self,messages,stage):
        """Retain numeric refusal codes and a fixed stage, never provider text."""
        if stage not in {'GREETING','AUTHENTICATION','STREAM'}:raise ValueError('INVALID_CONTROL_STAGE')
        if not isinstance(messages,list):return False
        rejected=False
        for message in messages:
            if isinstance(message,dict) and message.get('T')=='error':
                code=message.get('code')
                self.log('PROVIDER_REJECTION',provider_code=code if type(code) is int else None,reason=stage)
                rejected=True
        return rejected
    def pulse(self,now=None):
        now=now or datetime.now(timezone.utc);pause=self.probe.check(now)
        if pause:self.log('PROCESS_PAUSED',**pause)
        minute=now.replace(second=0,microsecond=0).isoformat()
        if self.minute and minute!=self.minute:
            self.log('MINUTE_MESSAGES',now=stamp(self.minute),count=self.message_count);self.message_count=0
        self.minute=minute
    def key(self,kind,symbol):
        # Single-exchange research must never overwrite SIP/core risk inputs.
        return ('research_'+kind+':'+symbol+':iex') if self.name=='iex' else kind+':'+symbol
    def status(self,state,**extra):self.store.put('stream:'+self.name,{'state':state,'at':iso(),'connection_id':self.connection_id,'connection_started_at':self.started.isoformat(),**extra})
    def symbols(self):return (self.store.get('subscriptions',[])[:30] if self.options else ['SPY'])
    def clock_rejection(self,source,received,kind):
        """Diagnose future payloads without accepting, buffering or retiming them."""
        self.clock_rejected_count+=1;tick=time.monotonic()
        if self.clock_rejected_count==1 or tick>=self.next_clock_record:self.log('CLOCK_REJECTION',count=self.clock_rejected_count,payload_type=kind)
        if tick<self.next_clock_record:return
        self.next_clock_record=tick+5
        key='stream_clock:'+self.name;old=self.store.get(key,{})
        state={'state':'FUTURE_TIMESTAMP_REJECTED','quality':'DATA_INVALID','provider':'alpaca-'+self.name,'at':received,'source_timestamp':source,'received_timestamp':received,'payload_type':kind,'ahead_seconds':(stamp(source)-stamp(received)).total_seconds(),'rejected_payloads_since_process_start':self.clock_rejected_count,'first_seen_at':old.get('first_seen_at',received) if old.get('state')=='FUTURE_TIMESTAMP_REJECTED' else received,'note':'Possible local/provider clock skew; future data remains rejected. A successful time-source check is separate.'}
        self.store.put(key,state)
        if old.get('state')!='FUTURE_TIMESTAMP_REJECTED':self.store.audit('clock-rejection-'+self.name+'-'+received,'future_timestamp_rejection','stream',{'feed':self.name,'ahead_seconds':state['ahead_seconds'],'source_timestamp':source,'received_timestamp':received})
    def clock_recovered(self,received):
        key='stream_clock:'+self.name;old=self.store.get(key,{})
        if old.get('state')!='FUTURE_TIMESTAMP_REJECTED':return
        self.store.put(key,{**old,'state':'CLEARED_BY_VALID_QUOTE','quality':'DATA_OK','at':received,'cleared_at':received,'note':'A fresh valid bid/ask was received without a future timestamp. This is not proof of system-clock synchronization.'})
        self.next_clock_record=0
        self.store.audit('clock-clear-'+self.name+'-'+received,'future_timestamp_condition_cleared','stream',{'feed':self.name,'at':received,'basis':'VALID_QUOTE_ONLY'})
    def ingest(self,msg,received=None):
        if not isinstance(msg,dict):return False
        kind=msg.get('T');symbol=msg.get('S');received=received or iso();ingest_started=time.perf_counter();writes={}
        queue_ms=(datetime.now(timezone.utc)-stamp(received)).total_seconds()*1000
        if kind not in ('q','t','b','u') or not isinstance(symbol,str) or not symbol:return False
        if symbol not in self.symbols():return False
        try:
            source=stamp(msg['t']);latency=(stamp(received)-source).total_seconds()
            if latency < -self.max_future_skew_seconds:self.clock_rejection(msg['t'],received,kind);return False
            if latency<0:self.store.put('stream_skew:'+self.name,{'state':'ACCEPTED_BOUNDED_SKEW','at':received,'source_timestamp':msg['t'],'ahead_seconds':-latency,'budget_seconds':self.max_future_skew_seconds})
            key=(symbol,'b' if kind=='u' else kind)
            cache_kind={'q':'quote','t':'trade','b':'stream_bar','u':'stream_bar'}[kind]
            cached=self.store.get(self.key(cache_kind,symbol)) or {}
            old=self.last_source.get(key)
            # The persisted source watermark survives process/socket restarts.
            # Receipt time is not a substitute for the provider's source time.
            try:
                persisted=stamp(cached['source_timestamp'])
                old=max(old,persisted) if old else persisted
            except (KeyError,TypeError,ValueError):pass
            if old and (source<old or (source==old and kind!='u')):
                self.log('DATA_REJECTION',reason='OUT_OF_ORDER' if source<old else 'DUPLICATE_SOURCE',payload_type=kind,source_age_seconds=latency)
                return False
            if kind=='q':
                d=quote('alpaca-'+self.name,symbol,msg,received=received).view(max_future_skew_seconds=self.max_future_skew_seconds)
                if d['quality']!=Quality.OK:
                    self.log('DATA_REJECTION',reason='QUOTE_QUALITY_REJECTED',payload_type=kind,source_age_seconds=latency)
                    return False
                writes[self.key('quote',symbol)]=d
                self.clock_recovered(received)
            elif kind=='t':
                if not finite(msg.get('p')) or msg['p']<=0:return False
                writes[self.key('trade',symbol)]=Datum('alpaca-'+self.name,symbol,'trade',msg['t'],received,Quality.OK,'REALTIME',{'price':msg['p'],'size':msg.get('s')},msg.get('i')).view()
            else:
                # Reject bad aggregates before persisting history or refreshing health.
                if not all(finite(msg.get(k)) and msg[k]>0 for k in ('o','h','l','c')):return False
                if not msg['l']<=min(msg['o'],msg['c'])<=max(msg['o'],msg['c'])<=msg['h']:return False
                if not finite(msg.get('v')) or msg['v']<0:return False
                if 'vw' in msg and (not finite(msg['vw']) or msg['vw']<=0):return False
                self.store.put(self.key('stream_bar',symbol),Datum('alpaca-'+self.name,symbol,'bar',msg['t'],received,Quality.OK,'REALTIME',msg).view(max_age=120))
                history_key=self.key('stream_bars',symbol)
                if hasattr(self.store,'merge_rows'):self.store.merge_rows(history_key,[msg],maximum=20000,incoming_wins=True)
                else:
                    rows=self.store.get(history_key,[]);rows=[r for r in rows if r['t']!=msg['t']];rows.append(msg);rows.sort(key=lambda r:r['t']);self.store.put(history_key,rows[-20000:])
            self.last_source[key]=source
            # Only fresh market payloads reset the watchdog; heartbeat/control frames do not.
            if latency<=15:
                writes['last_market:'+self.name]={'source_timestamp':msg['t'],'received_timestamp':received,'latency_ms':latency*1000}
                self.pulse(stamp(received));self.message_count+=1
                if not self.first:self.log('FIRST_MARKET_MESSAGE',latency_ms=latency*1000);self.first=True
            writes['stream:'+self.name]={'state':'CONNECTED','at':received,'connection_id':self.connection_id,'connection_started_at':self.started.isoformat(),'market_latency_ms':latency*1000,'local_queue_delay_ms':queue_ms,'ingest_processing_ms':(time.perf_counter()-ingest_started)*1000,'payload_type':kind,'reconnect_attempt':self.attempt}
            if hasattr(self.store,'put_many'):self.store.put_many(writes)
            else:
                for k,v in writes.items():self.store.put(k,v)
            if not self.options and kind=='q':
                from core.directional_research import capture_future_quote
                capture_future_quote(self.store,d,stamp(received))
            if self.options and kind=='q':
                # Prospective genuine observations only; no entitlement inference.
                self.store.event('option-observation:'+symbol+':'+msg['t'],'prospective_option_bbo',{'contract':symbol,'quote':d,'captured_at':received,'source':'AUTHENTICATED_OPRA_STREAM','entitlement_proof':'UNESTABLISHED','strategy_qualified':False})
            return True
        except (ValueError,KeyError,TypeError):return False
    async def run(self):
        if not os.getenv('APCA_API_KEY_ID') or not os.getenv('APCA_API_SECRET_KEY'):
            while not self.stop.is_set():self.status('FEED_NOT_CONFIGURED');await self.wait(30)
            return
        from websockets.asyncio.client import connect
        connector=self.connect or connect
        while not self.stop.is_set():
            symbols=self.symbols()
            if not symbols:self.status('IDLE_NO_CONTRACT_SUBSCRIPTIONS');await self.wait(10);continue
            try:
                start=time.monotonic();self.started=datetime.now(timezone.utc);self.connection_id=str(time.time_ns());self.first=False;self.pulse();self.status('CONNECTING');self.log('CONNECT')
                url='wss://stream.data.alpaca.markets/'+('v1beta1/opra' if self.options else 'v2/'+self.name)
                async with connector(url,additional_headers={'Content-Type':'application/msgpack'} if self.options else {},ping_interval=20,ping_timeout=20,open_timeout=15,close_timeout=5,max_queue=256) as ws:
                    connection_latency=(time.monotonic()-start)*1000
                    greeting=decode(await asyncio.wait_for(ws.recv(),10),self.options)
                    if self.record_provider_rejections(greeting,'GREETING'):raise PermissionError('GREETING_REJECTED')
                    await ws.send(encode({'action':'auth','key':os.environ['APCA_API_KEY_ID'],'secret':os.environ['APCA_API_SECRET_KEY']},self.options))
                    auth=decode(await asyncio.wait_for(ws.recv(),10),self.options)
                    if self.record_provider_rejections(auth,'AUTHENTICATION'):raise PermissionError('AUTH_REJECTED')
                    if not any(m.get('msg')=='authenticated' for m in auth):raise PermissionError('AUTH_REJECTED')
                    self.log('AUTHENTICATED',latency_ms=connection_latency)
                    subscription={'action':'subscribe','quotes':symbols,'trades':symbols}
                    if not self.options:subscription.update(bars=symbols,updatedBars=symbols)
                    await ws.send(encode(subscription,self.options));self.log('SUBSCRIBED');self.status('CONNECTED',connection_latency_ms=connection_latency);connected=time.monotonic()
                    while not self.stop.is_set():
                        self.pulse();clock=datetime.now(timezone.utc)
                        age=connection_watchdog_age(self.store.get('last_market:'+self.name) or {},clock,self.started)
                        if active(clock) and age>=90:
                            self.log('WATCHDOG_RECONNECT',duration_seconds=age,reason='NO_VALID_MARKET_MESSAGE')
                            raise TimeoutError('WATCHDOG_NO_MARKET_DATA')
                        try:raw=await asyncio.wait_for(ws.recv(),20)
                        except asyncio.TimeoutError:
                            self.status('CONNECTED_IDLE',connection_latency_ms=connection_latency)
                            if self.symbols()!=symbols:break
                            continue
                        received=iso() # Transport receipt, before decode, sorting or SQLite work.
                        messages=decode(raw,self.options)
                        if not isinstance(messages,list):raise ValueError('MALFORMED_STREAM_BATCH')
                        # Quote updates precede heavier bar merges in a provider batch.
                        messages.sort(key=lambda m:0 if isinstance(m,dict) and m.get('T')=='q' else 1)
                        for msg in messages:
                            if not isinstance(msg,dict):
                                self.log('DATA_REJECTION',reason='MALFORMED_STREAM_ITEM');continue
                            if msg.get('T')=='error':
                                self.record_provider_rejections([msg],'STREAM')
                                raise PermissionError('PROVIDER_STREAM_REJECTED')
                            try:self.ingest(msg,received=received)
                            except sqlite3.OperationalError:
                                self.log('DATA_REJECTION',reason='SQLITE_INGEST_FAILED',payload_type=msg.get('T'))
                                # Preserve the failure, not an unrelated network reconnect.
                                # Strict freshness naturally blocks the uncommitted quote.
                                continue
                        if time.monotonic()-connected>60:self.attempt=0
                        if self.symbols()!=symbols:break
            except asyncio.CancelledError:break
            except Exception as e:
                self.attempt+=1;delay=min(300,2**min(self.attempt,8))+random.random()
                if isinstance(e,PermissionError):delay=max(delay,300)
                self.log('PERMISSION_ERROR' if isinstance(e,PermissionError) else 'DISCONNECT',reason=type(e).__name__,close_code=getattr(getattr(e,'rcvd',None),'code',None))
                self.log('RECONNECT',attempt=self.attempt,backoff_seconds=delay)
                self.status('FEED_DISCONNECTED',reconnect_attempt=self.attempt,next_retry_seconds=delay,error_type=type(e).__name__)
                self.store.audit('reconnect-'+self.name+'-'+str(time.time_ns()),'provider_reconnect','stream',{'feed':self.name,'attempt':self.attempt,'error_type':type(e).__name__});await self.wait(delay)
        self.pulse();self.log('MINUTE_MESSAGES',count=self.message_count);self.status('STOPPED')
        if hasattr(self,'_events'):self._events.close()
    async def wait(self,seconds):
        try:await asyncio.wait_for(self.stop.wait(),seconds)
        except asyncio.TimeoutError:pass
def run_feed(feed,options,budget,shutdown):
    """Each feed owns its event loop and SQLite connection.

    A rejected SIP connection or a heavy bar merge cannot block IEX socket reads.
    This isolates local scheduling; it cannot repair delay at the provider.
    """
    async def run():
        store=Store();stream=Stream(store,options,feed=feed,max_future_skew_seconds=budget)
        async def watch():
            while not shutdown.is_set() and not (ROOT/'runtime/shutdown.request').exists() and not stream.stop.is_set():await asyncio.sleep(.5)
            stream.stop.set()
        try:await asyncio.gather(stream.run(),watch())
        finally:store.close()
    asyncio.run(run())

async def main():
    from core.upgrade_service import read_config
    import threading
    budget=read_config().get('max_future_skew_seconds',2.0);shutdown=threading.Event()
    def stop(*args):shutdown.set()
    signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
    try:await asyncio.gather(*(asyncio.to_thread(run_feed,feed,options,budget,shutdown) for feed,options in [('sip',False),('sip',True),('iex',False)]))
    finally:shutdown.set()
if __name__=='__main__':asyncio.run(main())
