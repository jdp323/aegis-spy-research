"""Transactional local state and append-only audit trail; no credentials in payloads."""
import hashlib,json,sqlite3,time
from time import monotonic as transaction_clock
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
def utcnow(): return datetime.now(timezone.utc)
def iso(): return utcnow().isoformat()
def encode(v): return json.dumps(v,sort_keys=True,allow_nan=False,default=str)
class Store:
    def __init__(self,path=None,lock_timeout=.5,retry_attempts=3,sleep=time.sleep):
        path=Path(path or ROOT/'runtime/aegis.sqlite');path.parent.mkdir(parents=True,exist_ok=True)
        self._closers=[]
        self.path=path;self.retry_attempts=retry_attempts;self.sleep=sleep
        if not 0<=lock_timeout<=2 or type(retry_attempts) is not int or not 1<=retry_attempts<=5:raise ValueError('INVALID_DATABASE_RETRY_POLICY')
        self.metrics={'transactions':0,'busy_retries':0,'failures':0,'last_duration_seconds':0,'maximum_duration_seconds':0,'lock_timeout_seconds':lock_timeout,'maximum_attempts':retry_attempts}
        self.db=sqlite3.connect(path,timeout=lock_timeout);self.db.row_factory=sqlite3.Row
        self.db.executescript('''PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY,payload TEXT,updated TEXT);
        CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,kind TEXT,payload TEXT,created TEXT);
        CREATE INDEX IF NOT EXISTS events_kind_created ON events(kind,created DESC);
        CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY,id TEXT UNIQUE,kind TEXT,actor TEXT,payload TEXT,created TEXT,previous TEXT,hash TEXT);
        CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit BEGIN SELECT RAISE(ABORT,'append only'); END;
        CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit BEGIN SELECT RAISE(ABORT,'append only'); END;''')
    def close(self):
        for close in self._closers:close()
        self._closers=[]
        self.db.close()
    def transaction(self,work):
        """Retry only SQLite busy/locked transactions after rollback, within bounds."""
        started=transaction_clock()
        try:
            for attempt in range(self.retry_attempts):
                try:
                    value=work();self.metrics['transactions']+=1;return value
                except sqlite3.OperationalError as error:
                    self.db.rollback();code=getattr(error,'sqlite_errorcode',None)
                    self.metrics['last_error_code']=code;self.metrics['last_error_name']=getattr(error,'sqlite_errorname','UNAVAILABLE')
                    busy=code is not None and code&255 in (sqlite3.SQLITE_BUSY,sqlite3.SQLITE_LOCKED)
                    if not busy or attempt+1>=self.retry_attempts:raise
                    self.metrics['busy_retries']+=1;self.sleep(.05*(2**attempt))
                except Exception:self.db.rollback();raise
        except Exception:
            self.metrics['failures']+=1;raise
        finally:
            duration=transaction_clock()-started;self.metrics['last_duration_seconds']=duration;self.metrics['maximum_duration_seconds']=max(duration,self.metrics['maximum_duration_seconds'])
    def put(self,key,value):
        from core.isolation import assert_real
        assert_real(value)
        body=encode(value);at=iso()
        def write():
            with self.db:self.db.execute('INSERT INTO state VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET payload=excluded.payload,updated=excluded.updated',(key,body,at))
        self.transaction(write)
    def put_many(self,values):
        from core.isolation import assert_real
        assert_real(values)
        at=iso();rows=[(k,encode(v),at) for k,v in values.items()]
        def write():
            with self.db:self.db.executemany('INSERT INTO state VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET payload=excluded.payload,updated=excluded.updated',rows)
        self.transaction(write)
    def get(self,key,default=None):
        r=self.db.execute('SELECT payload FROM state WHERE key=?',(key,)).fetchone();return json.loads(r[0]) if r else default
    def reserve(self,key,value):
        """Claim a durable slot once, including competing local producers."""
        from core.isolation import assert_real
        assert_real(value);body=encode(value);at=iso()
        def write():
            with self.db:cur=self.db.execute('INSERT OR IGNORE INTO state VALUES(?,?,?)',(key,body,at))
            return cur.rowcount==1
        return self.transaction(write)
    def merge_rows(self,key,rows,maximum=20000,incoming_wins=False,timestamp_key='t'):
        """Atomic history merge prevents a stream/backfill read-modify-write loss."""
        from core.isolation import assert_real
        from data.models import stamp
        assert_real(rows)
        if type(maximum) is not int or not 1<=maximum<=50000:raise ValueError('INVALID_HISTORY_LIMIT')
        # Build outside the writer lock. CAS prevents a concurrent stream/backfill
        # update from being lost; retry rebuilds from the new committed snapshot.
        started=transaction_clock()
        for conflict in range(self.retry_attempts):
            raw=self.db.execute('SELECT payload FROM state WHERE key=?',(key,)).fetchone()
            before=raw[0] if raw else None
            current=json.loads(before) if before else []
            def canonical(row):return stamp(row[timestamp_key]).astimezone(timezone.utc).isoformat()
            first,second=(current,rows) if incoming_wins else (rows,current)
            merged={canonical(row):row for row in first}
            merged.update({canonical(row):row for row in second})
            result=[merged[t] for t in sorted(merged)][-maximum:]
            body=encode(result);at=iso()
            def write():
                self.db.execute('BEGIN IMMEDIATE')
                live=self.db.execute('SELECT payload FROM state WHERE key=?',(key,)).fetchone()
                if (live[0] if live else None)!=before:
                    self.db.rollback();return False
                self.db.execute('INSERT INTO state VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET payload=excluded.payload,updated=excluded.updated',(key,body,at))
                self.db.commit();return True
            if self.transaction(write):
                self.metrics['merge_total_seconds']=transaction_clock()-started
                self.metrics['merge_rows']=len(result)
                return result
            self.metrics['merge_conflicts']=self.metrics.get('merge_conflicts',0)+1
        raise sqlite3.OperationalError('HISTORY_MERGE_CONCURRENT_UPDATE')
    def snapshot(self,keys):
        # One SQLite read transaction, clock taken by caller after this returns.
        self.db.execute('BEGIN')
        try:
            result={key:self.get(key) for key in keys};self.db.commit();return result
        except Exception:self.db.rollback();raise
    def event(self,id,kind,payload):
        from core.isolation import assert_real
        assert_real(payload)
        body=encode(payload);at=iso()
        def write():
            with self.db:cur=self.db.execute('INSERT OR IGNORE INTO events VALUES(?,?,?,?)',(id,kind,body,at))
            return cur.rowcount==1
        return self.transaction(write)
    def events(self,kind,limit=100):return [json.loads(r[0]) for r in self.db.execute('SELECT payload FROM events WHERE kind=? ORDER BY created DESC LIMIT ?',(kind,limit))]
    def audit(self,id,kind,actor,payload):
        from core.isolation import assert_real
        assert_real(payload)
        # Callers supply only explicitly safe fields; never raw request text/secrets.
        def write():
            self.db.execute('BEGIN IMMEDIATE')
            if self.db.execute('SELECT 1 FROM audit WHERE id=?',(id,)).fetchone():self.db.rollback();return
            row=self.db.execute('SELECT hash FROM audit ORDER BY seq DESC LIMIT 1').fetchone();previous=row[0] if row else 'GENESIS';stamp=iso();body=encode(payload)
            digest=hashlib.sha256(encode([id,kind,actor,body,stamp,previous]).encode()).hexdigest()
            self.db.execute('INSERT INTO audit(id,kind,actor,payload,created,previous,hash) VALUES(?,?,?,?,?,?,?)',(id,kind,actor,body,stamp,previous,digest));self.db.commit()
        return self.transaction(write)
