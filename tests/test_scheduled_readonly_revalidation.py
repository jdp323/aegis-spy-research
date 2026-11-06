"""Scheduled gate prerequisites: actual read-only facade/evaluator, fake inputs.

These cases grant no publication permission and do not exercise a transport.
"""
import copy,json,sqlite3,tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
from core.readonly_state import ReadOnlyState
from core.observed_context import evaluate
from core.sessions import ET

NOW=datetime(2026,11,6,11,15,tzinfo=ET).astimezone(timezone.utc)

class Frozen(datetime):
    current=NOW
    @classmethod
    def now(cls,tz=None):
        return cls.current.astimezone(tz) if tz else cls.current.replace(tzinfo=None)

class ReadOnlyRevalidation(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'fixture.sqlite'
        self.writer=sqlite3.connect(self.path,timeout=.25)
        self.addCleanup(self.writer.close)
        self.writer.execute('PRAGMA journal_mode=WAL')
        self.writer.execute('CREATE TABLE state(key TEXT PRIMARY KEY,payload TEXT,updated TEXT)')
        self.writer.commit()
        self.facade=ReadOnlyState(self.path);self.addCleanup(self.facade.close)
        Frozen.current=NOW
        self.clock=patch('core.observed_context.datetime',Frozen)
        self.clock.start();self.addCleanup(self.clock.stop)

    def put(self,key,value):
        self.writer.execute('INSERT OR REPLACE INTO state VALUES(?,?,?)',(key,json.dumps(value),NOW.isoformat()))
        self.writer.commit()

    def original(self):
        return list(self.writer.execute('SELECT key,payload,updated FROM state ORDER BY key'))

    def inputs(self):
        q={'provider':'alpaca-iex','quality':'DATA_OK','entitlement':'REALTIME',
           'feed_quality':'IEX','data_type':'quote','source_timestamp':(NOW-timedelta(seconds=1)).isoformat(),
           'received_timestamp':(NOW-timedelta(seconds=.5)).isoformat(),
           'payload':{'bid':600,'ask':600.02,'mid':600.01}}
        self.put('research_quote:SPY:iex',q)
        self.put('stream:iex',{'state':'CONNECTED','at':NOW.isoformat()})
        rows=[]
        for n in range(31):
            t=NOW.replace(second=0,microsecond=0)-timedelta(minutes=31-n)
            p=599+n*.02
            rows.append({'t':t.isoformat(),'o':p,'h':p+.05,'l':p-.05,'c':p+.01,'v':1000})
        self.put('research_stream_bars:SPY:iex',rows)
        return q,rows

    def observe(self):
        before=self.original();schema=list(self.writer.execute('SELECT type,name,sql FROM sqlite_master ORDER BY name'))
        result=evaluate(self.facade,NOW,simulation=False)
        self.assertEqual(self.original(),before)
        self.assertEqual(list(self.writer.execute('SELECT type,name,sql FROM sqlite_master ORDER BY name')),schema)
        self.assertFalse((self.path.parent/'observability.sqlite').exists())
        self.assertFalse(hasattr(self.facade,'path'),'Evaluator must not acquire a writable Store path')
        return result

    def test_missing_database_is_not_created(self):
        missing=self.path.parent/'missing.sqlite'
        with self.assertRaises(sqlite3.OperationalError):ReadOnlyState(missing)
        self.assertFalse(missing.exists())

    def test_put_is_noop_and_direct_sql_write_is_refused(self):
        self.put('sentinel',{'v':1});before=self.original()
        self.facade.put('sentinel',{'v':2})
        self.assertEqual(self.facade.get('sentinel'),{'v':1})
        self.assertEqual(self.facade.db.execute('PRAGMA query_only').fetchone()[0],1)
        with self.assertRaises(sqlite3.OperationalError):
            self.facade.db.execute("UPDATE state SET payload='{}'")
        self.assertEqual(self.original(),before)

    def test_snapshot_does_not_mix_concurrent_writer_revisions(self):
        self.put('left',{'v':1});self.put('right',{'v':1});native=self.facade.get;changed=[]
        def concurrent(key,default=None):
            result=native(key,default)
            if key=='left' and not changed:
                self.writer.execute('BEGIN IMMEDIATE')
                for name in ('left','right'):
                    self.writer.execute('UPDATE state SET payload=? WHERE key=?',(json.dumps({'v':2}),name))
                self.writer.commit();changed.append(True)
            return result
        with patch.object(self.facade,'get',side_effect=concurrent):
            self.assertEqual(self.facade.snapshot(('left','right')),{'left':{'v':1},'right':{'v':1}})
        self.assertFalse(self.facade.db.in_transaction)
        self.assertEqual(self.facade.snapshot(('left','right')),{'left':{'v':2},'right':{'v':2}})

    def test_actual_evaluator_preserves_fresh_iex_clocks_and_31_bar_population(self):
        quote,rows=self.inputs();result=self.observe()
        self.assertIsNone(result['reason']);self.assertEqual(result['feed_quality'],'IEX')
        self.assertEqual(result['quote'],quote);self.assertEqual(result['rows'],rows)
        self.assertEqual(len(result['bars']),31);self.assertFalse(result['early'])
        self.assertEqual(result['synthetic_continuity_minutes'],0)
        self.assertEqual(datetime.fromisoformat(result['evaluated_at']),NOW)

    def test_delayed_snapshot_uses_post_read_clock_and_rejects_original_quote(self):
        quote,_=self.inputs();native=self.facade.snapshot
        def delayed(keys):
            result=native(keys);Frozen.current=NOW+timedelta(seconds=6);return result
        with patch.object(self.facade,'snapshot',side_effect=delayed):result=self.observe()
        self.assertEqual(result['failed_predicate'],'SOURCE_TOO_OLD')
        self.assertEqual(result['evaluated_at'],Frozen.current.isoformat())
        self.assertEqual(self.facade.get('research_quote:SPY:iex'),quote)
        diag=next(d for d in result['diagnostics'] if d['provider']=='alpaca-iex')
        self.assertEqual(diag['source_age_seconds'],7)
        self.assertEqual(diag['receipt_age_seconds'],6.5)

    def test_future_source_or_receipt_remains_rejected_without_diagnostics_writes(self):
        quote,_=self.inputs()
        for field,predicate in (('source_timestamp','SOURCE_AFTER_CLOCK'),('received_timestamp','RECEIPT_AFTER_CLOCK')):
            with self.subTest(field=field):
                changed=copy.deepcopy(quote);changed[field]=(NOW+timedelta(seconds=1)).isoformat()
                self.put('research_quote:SPY:iex',changed);result=self.observe()
                self.assertEqual(result['failed_predicate'],predicate)
                self.assertEqual(self.facade.get('research_quote:SPY:iex'),changed)

    def test_existing_heartbeat_and_continuity_gates_survive_readonly_facade(self):
        _,rows=self.inputs()
        self.put('stream:iex',{'state':'CONNECTED','at':(NOW-timedelta(seconds=31)).isoformat()})
        self.assertEqual(self.observe()['failed_predicate'],'HEARTBEAT_AGE')
        self.put('stream:iex',{'state':'CONNECTED','at':NOW.isoformat()})
        self.put('research_stream_bars:SPY:iex',rows[:12]+rows[13:])
        result=self.observe()
        self.assertEqual(result['failed_predicate'],'BAR_TAIL_GAP')
        self.assertEqual(self.facade.get('research_stream_bars:SPY:iex'),rows[:12]+rows[13:])

    def test_snapshot_read_error_rolls_back_and_never_returns_partial_context(self):
        self.put('left',{'v':1});before=self.original();native=self.facade.get
        def fail(key,default=None):
            if key=='right':raise sqlite3.OperationalError('OFFLINE_INJECTED_READ_FAILURE')
            return native(key,default)
        with patch.object(self.facade,'get',side_effect=fail):
            with self.assertRaises(sqlite3.OperationalError):self.facade.snapshot(('left','right'))
        self.assertFalse(self.facade.db.in_transaction)
        self.assertEqual(self.original(),before)
