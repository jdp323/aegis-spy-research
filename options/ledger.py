"""SPY long-option reports. Decimal cash arithmetic, durable idempotency; no orders."""
import json, re, sqlite3
from decimal import Decimal
from datetime import datetime, timezone

def contract(value):
    m=re.fullmatch(r'SPY(\d{6})([CP])(\d{8})',value)
    if not m: raise ValueError('Use standard SPY OCC symbol: SPYYYMMDDC/P######## (strike x1000).')
    expiry=datetime.strptime(m[1],'%y%m%d').date()
    strike=Decimal(m[3])/1000
    if strike<=0:raise ValueError('Strike must be positive')
    return {'symbol':value,'expiry':expiry.isoformat(),'type':m[2],'strike':str(strike),'multiplier':100,'currency':'USD'}

def amount(v):
    d=Decimal(str(v))
    if not d.is_finite() or d<0 or d>Decimal('10000000') or d.as_tuple().exponent < -4:raise ValueError('Invalid nonnegative amount; at most four decimals')
    return d

class Ledger:
    def __init__(self,path):
        self.db=sqlite3.connect(path,timeout=10,isolation_level=None)
        self.db.row_factory=sqlite3.Row
        self.db.executescript('''PRAGMA journal_mode=WAL;
          CREATE TABLE IF NOT EXISTS option_events(seq INTEGER PRIMARY KEY AUTOINCREMENT,id TEXT UNIQUE NOT NULL,payload TEXT NOT NULL,created TEXT NOT NULL);
          CREATE TRIGGER IF NOT EXISTS option_no_update BEFORE UPDATE ON option_events BEGIN SELECT RAISE(ABORT,'append only'); END;
          CREATE TRIGGER IF NOT EXISTS option_no_delete BEFORE DELETE ON option_events BEGIN SELECT RAISE(ABORT,'append only'); END;''')
    def close(self):self.db.close()
    def effective_events(self,extra_void=None):
        rows=[{**json.loads(r['payload']),'event_id':r['id']} for r in self.db.execute('SELECT id,payload FROM option_events ORDER BY seq')]
        voided={r['target_event_id'] for r in rows if r['side']=='VOID'}
        if extra_void:voided.add(extra_void)
        return [r for r in rows if r['side']!='VOID' and r['event_id'] not in voided]
    def positions(self,extra_void=None):
        book={}
        for e in self.effective_events(extra_void):
            p=book.setdefault(e['contract'],{'contract':e['contract'],'quantity':0,'cost_usd':Decimal(0),'realized_usd':Decimal(0)})
            q=e['quantity'];cash=Decimal(e['premium'])*100*q;fees=Decimal(e['fees'])
            if e['side']=='BUY':p['quantity']+=q;p['cost_usd']+=cash+fees
            else:
                if q>p['quantity']:raise ValueError('Reversal would make a position negative; reconcile dependent sales first')
                basis=p['cost_usd']*q/p['quantity'];p['quantity']-=q;p['cost_usd']-=basis;p['realized_usd']+=cash-fees-basis
        return [{**p,'cost_usd':str(p['cost_usd']),'realized_usd':str(p['realized_usd']),'source':'USER_REPORTED','quote':None} for p in book.values()]
    def record(self,event_id,side,symbol,quantity,premium,fees,filled_at,*,force=False,signal_id=None):
        spec=contract(symbol)
        if side not in ('BUY','SELL') or type(quantity) is not int or quantity<=0 or quantity>100000:raise ValueError('BUY/SELL and positive integer contracts required')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',event_id):raise ValueError('Invalid event id')
        px=amount(premium);fee=amount(fees)
        if side=='BUY' and px==0:raise ValueError('Purchase premium must be positive')
        stamp=datetime.fromisoformat(filled_at.replace('Z','+00:00'))
        if stamp.tzinfo is None or stamp>datetime.now(timezone.utc):raise ValueError('Fill needs a past timestamp with timezone')
        from core.sessions import ET
        if stamp.astimezone(ET).date()>datetime.fromisoformat(spec['expiry']).date():raise ValueError('Fill is after contract expiration')
        if type(force) is not bool or signal_id is not None and not re.fullmatch('[a-f0-9]{24}',signal_id):raise ValueError('Invalid report metadata')
        value={'side':side,'contract':symbol,'quantity':quantity,'premium':str(px),'fees':str(fee),'filled_at':stamp.astimezone(timezone.utc).isoformat(),'schema_version':2}
        if signal_id:value['signal_id']=signal_id
        if force:value['duplicate_override']=True
        payload=json.dumps(value,sort_keys=True)
        def same(a):return a.get('side')==side and a.get('contract')==symbol and a.get('quantity')==quantity and Decimal(a.get('premium','-1'))==px and Decimal(a.get('fees','-1'))==fee and datetime.fromisoformat(a['filled_at'])==stamp
        self.db.execute('BEGIN IMMEDIATE')
        try:
            old=self.db.execute('SELECT payload FROM option_events WHERE id=?',(event_id,)).fetchone()
            if old:
                if not same(json.loads(old[0])):raise ValueError('Event ID reused with different report')
                self.db.execute('COMMIT');return 'ALREADY_RECORDED'
            if not force and any(same(e) for e in self.effective_events()):raise ValueError('Exact duplicate fill rejected. Append FORCE only if this is a separate actual fill.')
            if side=='SELL':
                held=next((p['quantity'] for p in self.positions() if p['contract']==symbol),0)
                if quantity>held:raise ValueError('Sale exceeds reported holding; short options unsupported')
            previous=self.effective_events()
            if previous and stamp<datetime.fromisoformat(previous[-1]['filled_at']):raise ValueError('Out-of-order fill needs manual reconciliation')
            self.db.execute('INSERT INTO option_events(id,payload,created) VALUES(?,?,?)',(event_id,payload,datetime.now(timezone.utc).isoformat()))
            self.db.execute('COMMIT');return 'RECORDED_USER_REPORT'
        except Exception:self.db.execute('ROLLBACK');raise
    def void(self,event_id,target_event_id):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',event_id) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',target_event_id):raise ValueError('Invalid event id')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            old=self.db.execute('SELECT payload FROM option_events WHERE id=?',(event_id,)).fetchone()
            if old:
                if json.loads(old[0]).get('target_event_id')!=target_event_id:raise ValueError('Event ID reused')
                self.db.execute('COMMIT');return 'ALREADY_RECORDED'
            target=next((e for e in self.effective_events() if e['event_id']==target_event_id),None)
            if target is None:raise ValueError('Active fill event not found in your private ledger')
            self.positions(extra_void=target_event_id)
            at=datetime.now(timezone.utc).isoformat();payload={'schema_version':2,'side':'VOID','target_event_id':target_event_id,'contract':target['contract'],'voided_at':at,'source':'USER_REQUESTED_CORRECTION'}
            self.db.execute('INSERT INTO option_events(id,payload,created) VALUES(?,?,?)',(event_id,json.dumps(payload,sort_keys=True),at));self.db.execute('COMMIT');return 'REVERSAL_APPENDED'
        except Exception:self.db.execute('ROLLBACK');raise
