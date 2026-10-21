"""Complete, same-feed authorized history only; no fabricated OHLC storage."""
import hashlib,json,sqlite3,math,time,threading,queue
from datetime import datetime,timezone,timedelta
from core.sessions import ET,market_session
from data.reliability import active
from core.isolation import assert_real
from data.models import stamp,finite

def history(provider,start,end,feed='iex',timeframe='1Min'):
    if feed not in ('iex','sip') or timeframe not in ('1Min','5Min','15Min','30Min','1Hour','1Day'):raise ValueError('UNSUPPORTED_HISTORY')
    if start.tzinfo is None or end.tzinfo is None or end<=start:raise ValueError('INVALID_HISTORY_RANGE')
    rows=[];token=None;tokens=set();deadline=time.monotonic()+60
    for _ in range(30):
        # A bounded complete response is required. Partial pages cannot establish
        # absent minutes; no confirmations are published after a budget failure.
        if time.monotonic()>=deadline:raise ValueError('HISTORY_DEADLINE_EXCEEDED')
        p={'feed':feed,'timeframe':timeframe,'start':start.astimezone(timezone.utc).isoformat(),'end':end.astimezone(timezone.utc).isoformat(),'limit':10000,'adjustment':'raw','sort':'asc'}
        if token:p['page_token']=token
        result=provider.get('/v2/stocks/SPY/bars',p)
        if not isinstance(result,dict) or not isinstance(result.get('bars'),list):raise ValueError('MALFORMED_HISTORY_RESPONSE')
        assert_real(result)
        if result.get('symbol','SPY')!='SPY' or result.get('feed',feed)!=feed:raise ValueError('PROVIDER_FEED_MISMATCH')
        for row in result['bars']:
            t=stamp(row['t'])
            if not start<=t<=end or not all(finite(row.get(k)) and row[k]>0 for k in ('o','h','l','c')) or not finite(row.get('v')) or row['v']<0 or not row['l']<=min(row['o'],row['c'])<=max(row['o'],row['c'])<=row['h']:raise ValueError('INVALID_HISTORY_BAR')
            if timeframe=='1Min' and (t.second or t.microsecond):raise ValueError('UNALIGNED_HISTORY_BAR')
            rows.append({**row,'source':'REST_BACKFILL','provider':'alpaca-'+feed,'feed_quality':feed.upper()})
        token=result.get('next_page_token')
        if not token:
            unique={stamp(r['t']).astimezone(timezone.utc).isoformat():r for r in rows}
            fetched=datetime.now(timezone.utc).isoformat()
            return [dict(row,historical_retrieval_at=fetched) for row in sorted(unique.values(),key=lambda r:stamp(r['t']))]
        if not isinstance(token,str) or token in tokens:raise ValueError('PAGINATION_INVALID')
        tokens.add(token)
    raise ValueError('PAGINATION_INCOMPLETE')

def continuity(real,confirmed,start,end,maximum=2):
    """Returns transient slots ONLY. Must never feed indicators, fills or stores."""
    by={int(b['timestamp']):b for b in real};slots=[];count=0;previous=None
    prior=[b for b in real if b['timestamp']<start]
    if prior:previous=max(prior,key=lambda b:b['timestamp'])['close']
    for t in range(int(start),int(end)+1,60):
        if t in by:slot=by[t];previous=slot['close']
        elif t in confirmed and previous is not None:
            count+=1
            if count>maximum:raise ValueError('CONFIRMED_EMPTY_LIMIT_EXCEEDED')
            slot={'timestamp':t,'close':previous,'volume':0,'synthetic':True,'continuity_only':True,'confirmation':'NO_PRINT_CONFIRMED'}
        else:raise ValueError('UNCONFIRMED_MINUTE_GAP')
        slots.append(slot)
    return slots,count

class Backfill:
    def __init__(self,path,provider):
        path.parent.mkdir(parents=True,exist_ok=True);self.provider=provider;self.db=sqlite3.connect(path,timeout=15);self.next={};self.connections={};self.warmed=set();self.opening_attempted=set()
        from data.providers import AlpacaProvider
        # A denied SIP poll must not impose its entitlement cooldown on permitted
        # IEX history. Existing process authentication stays inside the adapter.
        if type(provider) is AlpacaProvider:self.provider=AlpacaProvider(provider.transport)
        self.db.executescript('''CREATE TABLE IF NOT EXISTS bar_confirmations(feed TEXT,timestamp TEXT,verified_at TEXT,evidence_hash TEXT,basis TEXT,PRIMARY KEY(feed,timestamp));
        CREATE TABLE IF NOT EXISTS backfill_runs(id INTEGER PRIMARY KEY,feed TEXT,start TEXT,end TEXT,fetched_at TEXT,status TEXT,bar_count INTEGER,confirmed_count INTEGER,reason TEXT);
        CREATE TRIGGER IF NOT EXISTS confirmation_no_delete BEFORE DELETE ON bar_confirmations BEGIN SELECT RAISE(ABORT,'append only'); END;
        CREATE TRIGGER IF NOT EXISTS confirmation_no_update BEFORE UPDATE ON bar_confirmations BEGIN SELECT RAISE(ABORT,'append only'); END;''')
    def close(self):self.db.close()
    def run(self,store,now,feed='iex',warmup=False,opening_only=False,tail_only=False):
        end=now.replace(second=0,microsecond=0)-timedelta(minutes=2)
        start=now.astimezone(ET).replace(hour=4,minute=0,second=0,microsecond=0).astimezone(timezone.utc)
        if tail_only:
            end=now.replace(second=0,microsecond=0)-timedelta(minutes=1)
            start=max(start,end-timedelta(minutes=4))
        if warmup:start=end-timedelta(days=45)
        if opening_only:
            start=now.astimezone(ET).replace(hour=9,minute=30,second=0,microsecond=0).astimezone(timezone.utc)
            end=start+timedelta(minutes=14)
            if end+timedelta(minutes=1)>now:raise ValueError('OPENING_RANGE_NOT_COMPLETE')
        rows=[];confirmed=0;reason=None
        try:
            rows=history(self.provider,start,end,feed)
            if not rows:raise ValueError('EMPTY_RESPONSE_NO_CONFIRMED_COVERAGE')
            stamps={stamp(r['t']).replace(second=0,microsecond=0) for r in rows}
            digest=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
            # Only bounded omissions inside a completely returned range. These are
            # no eligible provider aggregate, never proof of no consolidated trade.
            low=min(stamps);high=max(stamps)
            fetched=datetime.now(timezone.utc).isoformat()
            with self.db:
                t=low
                while t<=high:
                    if t not in stamps and market_session(t)['active']:
                        confirmed+=self.db.execute('INSERT OR IGNORE INTO bar_confirmations VALUES(?,?,?,?,?)',(feed,t.isoformat(),fetched,digest,'NO_PRINT_CONFIRMED: complete same-feed eligible aggregate response bounded by genuine bars')).rowcount
                    t+=timedelta(minutes=1)
            key='research_stream_bars:SPY:iex' if feed=='iex' else 'stream_bars:SPY'
            # Preserve captured stream provenance atomically against concurrent
            # minute arrival. Memory fixtures implement the same deterministic merge.
            if hasattr(store,'merge_rows'):store.merge_rows(key,rows,maximum=20000,incoming_wins=False)
            else:
                merged={stamp(r['t']).isoformat():r for r in rows}
                for r in store.get(key,[]) or []:merged[stamp(r['t']).isoformat()]=r
                store.put(key,sorted(merged.values(),key=lambda r:stamp(r['t']))[-20000:])
            day=now.astimezone(ET).date();empty=[int(stamp(r[0]).timestamp()) for r in self.db.execute('SELECT timestamp FROM bar_confirmations WHERE feed=?',(feed,)) if stamp(r[0]).astimezone(ET).date()==day and stamp(r[0]) not in stamps]
            store.put('confirmed_minutes:'+feed,empty)
            if warmup:
                daily=history(self.provider,end-timedelta(days=400),end,feed,'1Day')
                store.put('history_daily:'+feed,daily)
            if not opening_only and not tail_only:
                frames=store.get('history_frames:'+feed,{}) or {}
                for label,timeframe in (('5m','5Min'),('15m','15Min'),('30m','30Min'),('1h','1Hour')):
                    incoming=history(self.provider,start,end,feed,timeframe)
                    combined={stamp(r['t']).isoformat():r for r in frames.get(label,[])}
                    combined.update({stamp(r['t']).isoformat():r for r in incoming})
                    frames[label]=sorted(combined.values(),key=lambda r:stamp(r['t']))[-4000:]
                store.put('history_frames:'+feed,frames)
            if warmup:
                self.warmed.add((feed,day.isoformat()))
            status='DATA_OK'
        except Exception as e:
            status='UNAVAILABLE';reason=type(e).__name__
            codes={'UNSUPPORTED_HISTORY','INVALID_HISTORY_RANGE','MALFORMED_HISTORY_RESPONSE','PROVIDER_FEED_MISMATCH','INVALID_HISTORY_BAR','UNALIGNED_HISTORY_BAR','PAGINATION_INVALID','PAGINATION_INCOMPLETE','HISTORY_DEADLINE_EXCEEDED','EMPTY_RESPONSE_NO_CONFIRMED_COVERAGE','PROVIDER_BODY_LIMIT','PROVIDER_RESPONSE_NOT_OBJECT'}
            if isinstance(e,ValueError) and str(e) in codes:reason=str(e)
            if isinstance(e,RuntimeError) and str(e) in ('HTTP_401','HTTP_403','HTTP_429','FEED_NOT_CONFIGURED','RATE_LIMIT_COOLDOWN'):reason=str(e)
        fetched=datetime.now(timezone.utc).isoformat()
        with self.db:self.db.execute('INSERT INTO backfill_runs(feed,start,end,fetched_at,status,bar_count,confirmed_count,reason) VALUES(?,?,?,?,?,?,?,?)',(feed,start.isoformat(),end.isoformat(),fetched,status,len(rows),confirmed,reason))
        result={'at':fetched,'requested_at':now.isoformat(),'status':status,'feed_quality':feed.upper(),'source':'REST_BACKFILL','bars':len(rows),'confirmed':confirmed,'reason':reason}
        store.put('backfill_health:'+feed,result);return result
    def tick(self,store,now):
        if self.provider.health()['status']=='FEED_NOT_CONFIGURED':return
        feeds=['iex']
        if (store.get('stream:sip') or {}).get('state') in ('CONNECTED','CONNECTED_IDLE'):feeds.append('sip')
        for feed in feeds:
            connection=(store.get('stream:'+feed) or {}).get('connection_id')
            warm=(feed,now.astimezone(ET).date().isoformat()) not in self.warmed
            from data.reliability import active
            if not warm and not active(now):continue
            day=now.astimezone(ET).date().isoformat();minute=now.astimezone(ET).hour*60+now.astimezone(ET).minute
            if active(now) and minute>=585 and (feed,day) not in self.opening_attempted:
                key='research_stream_bars:SPY:iex' if feed=='iex' else 'stream_bars:SPY'
                opening=now.astimezone(ET).replace(hour=9,minute=30,second=0,microsecond=0).timestamp()
                captured={stamp(r['t']).timestamp() for r in store.get(key,[]) or []}
                if any(opening+i*60 not in captured for i in range(15)):
                    self.opening_attempted.add((feed,day));self.run(store,now,feed,opening_only=True)
            if now.timestamp()<self.next.get(feed,0) and connection==self.connections.get(feed):continue
            self.next[feed]=now.timestamp()+300;self.connections[feed]=connection
            self.run(store,now,feed,warmup=warm)


class BackgroundBackfill:
    """One history worker with its own SQLite handles and a single pending tick.

    The main worker never waits for history. In-flight requests keep their real
    adapter timeouts; an over-budget request is reported, never called canceled.
    Warmup/cooldowns survive across tasks within this history worker.
    """
    def __init__(self,path,store_path,provider,tail_only=False):
        self.path=path;self.store_path=store_path;self.provider=provider;self.tail_only=tail_only;self.tail_minute=None
        self.pending=queue.Queue(maxsize=1);self.stop=threading.Event();self.thread=None
        self.lock=threading.Lock();self.progress={'state':'IDLE','at':datetime.now(timezone.utc).isoformat()}
    def _run(self):
        from core.storage import Store
        from core.background_jobs import error_fields
        store=None;backfill=None
        try:
            store=Store(self.store_path);backfill=Backfill(self.path,self.provider)
            while not self.stop.is_set():
                try:now=self.pending.get(timeout=.2)
                except queue.Empty:continue
                started=time.monotonic()
                with self.lock:self.progress={'state':'RUNNING','at':datetime.now(timezone.utc).isoformat(),'started_monotonic':started}
                try:
                    if self.tail_only:
                        key=now.replace(second=0,microsecond=0).isoformat()
                        if active(now) and now.astimezone(ET).hour*60+now.astimezone(ET).minute>=571 and key!=self.tail_minute:
                            self.tail_minute=key;backfill.run(store,now,'iex',tail_only=True)
                    else:backfill.tick(store,now)
                    result={'state':'COMPLETED'}
                except Exception as error:result={'state':'FAILED',**error_fields(error)}
                with self.lock:self.progress={**result,'at':datetime.now(timezone.utc).isoformat(),'duration_seconds':time.monotonic()-started}
        except Exception as error:
            with self.lock:self.progress={'state':'FAILED','at':datetime.now(timezone.utc).isoformat(),**error_fields(error)}
        finally:
            if backfill:backfill.close()
            if store:store.close()
    def tick(self,store,now):
        if self.stop.is_set():return
        if self.thread is None:
            self.thread=threading.Thread(target=self._run,name='aegis-history',daemon=True);self.thread.start()
        try:self.pending.put_nowait(now)
        except queue.Full:
            # Keep the latest target window while a long request is in flight.
            # This is not a receipt/source timestamp and never refreshes a quote.
            try:self.pending.get_nowait()
            except queue.Empty:pass
            try:self.pending.put_nowait(now)
            except queue.Full:pass
    def health(self):
        with self.lock:result=dict(self.progress)
        started=result.pop('started_monotonic',None)
        if started is not None:
            result['elapsed_seconds']=time.monotonic()-started
            if result['elapsed_seconds']>60:result['state']='RUNNING_OVER_BUDGET'
        return {**result,'thread_alive':bool(self.thread and self.thread.is_alive()),'pending_ticks':self.pending.qsize(),'analysis_blocked':False}
    def close(self):
        self.stop.set()
        if self.thread:self.thread.join(timeout=1)
