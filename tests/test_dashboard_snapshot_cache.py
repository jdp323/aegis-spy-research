import copy,json,sqlite3,tempfile,threading,unittest,urllib.request
from datetime import datetime,timedelta,timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from app import Handler
from core.storage import Store
from data.models import quote
from dashboard.snapshot_cache import SnapshotCache

NOW=datetime(2026,10,14,15,tzinfo=timezone.utc)

class Clock:
    def __init__(self):self.seconds=0
    def now(self):return NOW+timedelta(seconds=self.seconds)
    def mono(self):return self.seconds

def fixture():
    q=lambda provider,symbol:quote(provider,symbol,{'bp':499.99 if symbol=='SPY' else 1.9,'ap':500.01 if symbol=='SPY' else 2.1,'t':NOW.isoformat()},received=NOW.isoformat()).view(NOW)
    option={'symbol':'SPY261016C00500000','quote':q('alpaca-opra','SPY261016C00500000')}
    return {'generated_at':NOW.isoformat(),'session':{'timestamp':NOW.isoformat(),'state':'REGULAR'},
            'underlying':q('alpaca-sip','SPY'),'research_underlying':q('alpaca-iex','SPY'),
            'selection':{'best_contract':option},'streams':{'iex':{'at':NOW.isoformat(),'state':'CONNECTED'}},
            'signals':[{'signal_id':'fixture','signal_expiry':(NOW+timedelta(seconds=8)).isoformat(),'paper_eligible':True,'actionable':True,'live_signal_ready':True,'option_contract':copy.deepcopy(option)}],
            'positions':[{'contract':option['symbol'],'quantity':1,'estimated_pnl_usd':20,'estimated_liquidation_usd':220,'status':'OPEN'}],
            'options_readiness':{'gates':{'DATA_READY':True,'OPTIONS_READY':True,'LIVE_SIGNAL_READY':True}},
            'live_trend':{'status':'LIVE_TREND'},'today_verdict':'BUY CALL idea fixture','live_signal_enabled':True,'order_execution_enabled':True}

def loaded(clock=None,loader=fixture):
    clock=clock or Clock();cache=SnapshotCache(loader,refresh_seconds=999,clock=clock.now,monotonic=clock.mono)
    cache.get();cache.thread.join(2)
    if cache.thread.is_alive():raise AssertionError('fixture snapshot producer did not complete')
    return cache,clock

class SnapshotCacheTests(unittest.TestCase):
    def test_single_flight_nonblocking_default_schema_and_refresh_deadline(self):
        gate=threading.Event();calls=[];clock=Clock()
        def slow():calls.append(1);gate.wait(3);return fixture()
        cache=SnapshotCache(slow,clock=clock.now,monotonic=clock.mono)
        try:
            first=cache.get()
            for _ in range(20):cache.get()
            self.assertEqual(len(calls),1);self.assertFalse(first['snapshot_cache']['data_available'])
            self.assertIsNone(first['positions']);self.assertIn('no position closure inferred',first['today_verdict'])
            for key,kind in [('session',dict),('underlying',dict),('features',dict),('selection',dict),('signals',list)]:self.assertIsInstance(first[key],kind)
            clock.seconds=6;self.assertEqual(cache.get()['snapshot_cache']['state'],'REFRESH_OVERDUE')
            self.assertEqual(len(calls),1)
        finally:gate.set();cache.thread.join(3)

    def test_young_cache_cannot_freshen_old_bid_ask_or_expired_signal(self):
        cache,clock=loaded();clock.seconds=20;data=cache.get()
        self.assertTrue(data['snapshot_cache']['data_available'])
        self.assertEqual(data['underlying']['quality'],'DATA_STALE')
        self.assertEqual(data['underlying']['source_timestamp'],NOW.isoformat())
        self.assertEqual(data['underlying']['dashboard_recheck']['source_age_seconds'],20)
        self.assertTrue(data['streams']['iex']['fresh_heartbeat'])
        self.assertIsNone(data['selection']['best_contract'])
        self.assertEqual(data['signals'][0]['display_status'],'EXPIRED')
        self.assertFalse(data['signals'][0]['paper_eligible']);self.assertIsNone(data['signals'][0]['option_contract'])
        self.assertEqual(data['generated_at'],NOW.isoformat())

    def test_every_cached_gate_is_diagnostic_only_even_with_genuinely_fresh_quote(self):
        cache,_=loaded();data=cache.get()
        self.assertEqual(data['underlying']['quality'],'DATA_OK')
        self.assertFalse(data['snapshot_cache']['new_entry_eligibility'])
        self.assertTrue(all(value is False for value in data['options_readiness']['gates'].values()))
        for flag in ('live_signal_enabled','order_execution_enabled','live_execution_enabled','LIVE_SIGNAL_READY'):self.assertFalse(data[flag])
        self.assertFalse(data['signals'][0]['actionable']);self.assertFalse(data['signals'][0]['live_signal_ready'])
        self.assertEqual(data['live_trend']['status'],'DIAGNOSTIC_SNAPSHOT_ONLY')
        self.assertEqual(data['positions'][0]['status'],'OPEN');self.assertEqual(data['positions'][0]['quantity'],1)
        self.assertIsNone(data['positions'][0]['estimated_pnl_usd'])
        self.assertEqual(fixture()['signals'][0]['paper_eligible'],True)

    def test_source_and_receipt_boundaries_remain_strict_signed_and_independent(self):
        cache,clock=loaded();clock.seconds=5
        self.assertEqual(cache.get()['underlying']['quality'],'DATA_OK')
        clock.seconds=5.001;self.assertEqual(cache.get()['underlying']['quality'],'DATA_STALE')
        value=fixture();future=(NOW+timedelta(seconds=.1)).isoformat()
        value['underlying'].update(source_timestamp=future,received_timestamp=future,accepted_future_skew_seconds=2)
        other,_=loaded(loader=lambda:value);quote_now=other.get()['underlying']
        self.assertEqual(quote_now['dashboard_recheck']['receipt_age_seconds'],-.1)
        self.assertEqual(quote_now['dashboard_recheck']['predicate'],'RECEIPT_AFTER_CLOCK')
        self.assertEqual(quote_now['quality'],'DATA_STALE')

    def test_expired_or_future_snapshot_is_unavailable_without_claiming_closed_positions(self):
        cache,clock=loaded();clock.seconds=46;data=cache.get()
        self.assertFalse(data['snapshot_cache']['data_available']);self.assertIsNone(data['positions'])
        self.assertEqual(data['snapshot_cache']['snapshot_as_of'],NOW.isoformat())
        self.assertIn('no position closure inferred',data['today_verdict'])
        value=fixture();value['generated_at']=(NOW+timedelta(seconds=1)).isoformat()
        other,_=loaded(loader=lambda:value);self.assertFalse(other.get()['snapshot_cache']['data_available'])

    def test_loader_errors_do_not_expose_exception_text_or_spawn_retry_storm(self):
        calls=[];clock=Clock()
        def failing():calls.append(1);raise RuntimeError('sensitive free-form exception must never appear')
        cache=SnapshotCache(failing,clock=clock.now,monotonic=clock.mono);cache.get();cache.thread.join(2)
        for _ in range(20):data=cache.get()
        self.assertEqual(len(calls),1);self.assertEqual(data['snapshot_cache']['refresh_error_type'],'RuntimeError')
        self.assertNotIn('sensitive',json.dumps(data));self.assertEqual(data['snapshot_cache']['state'],'REFRESH_FAILED')

    def test_malformed_quote_does_not_break_default_http_shape(self):
        value=fixture();value['underlying']={'quality':'DATA_OK','source_timestamp':99,'received_timestamp':{},'payload':None}
        cache,_=loaded(loader=lambda:value);data=cache.get()
        self.assertEqual(data['underlying']['quality'],'DATA_STALE');self.assertFalse(data['signals'][0]['paper_eligible'])

    def test_upgrade_http_returns_while_producer_is_blocked(self):
        gate=threading.Event();clock=Clock()
        cache=SnapshotCache(lambda:(gate.wait(3),fixture())[1],clock=clock.now,monotonic=clock.mono)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.upgrade_snapshot_cache=cache
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with urllib.request.urlopen('http://127.0.0.1:'+str(server.server_port)+'/api/upgrade',timeout=1.5) as response:
                data=json.load(response);self.assertEqual(response.status,200)
            self.assertFalse(gate.is_set());self.assertFalse(data['snapshot_cache']['data_available'])
            self.assertFalse(data['LIVE_SIGNAL_READY'])
        finally:gate.set();server.shutdown();server.server_close();thread.join();cache.thread.join(3)

class EventIndexMigration(unittest.TestCase):
    def test_online_backup_then_idempotent_index_preserves_rows_and_query_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'legacy.sqlite';db=sqlite3.connect(path)
            db.execute('PRAGMA journal_mode=WAL');db.execute('CREATE TABLE events(id TEXT PRIMARY KEY,kind TEXT,payload TEXT,created TEXT)')
            for index in range(2000):db.execute('INSERT INTO events VALUES(?,?,?,?)',('fixture-'+str(index),'signal' if index%7==0 else 'other',json.dumps({'value':index}),'2026-10-14T15:'+str(index//100).zfill(2)+':00+00:00'))
            db.commit();query='SELECT payload FROM events WHERE kind=? ORDER BY created DESC LIMIT ?'
            before=db.execute(query,('signal',30)).fetchall();before_rows=db.execute('SELECT id,kind,payload,created FROM events ORDER BY id').fetchall();scan=[row[3] for row in db.execute('EXPLAIN QUERY PLAN '+query,('signal',30))]
            self.assertTrue(any('SCAN events' in value for value in scan))
            backup=sqlite3.connect(Path(tmp)/'backup.sqlite');db.backup(backup);self.assertEqual(backup.execute('SELECT count(*) FROM events').fetchone()[0],2000);backup.close();db.close()
            store=Store(path)
            try:
                after=[(row[0],) for row in store.db.execute(query,('signal',30))];self.assertEqual(before,after)
                self.assertEqual(before_rows,[tuple(row) for row in store.db.execute('SELECT id,kind,payload,created FROM events ORDER BY id')])
                plan=[row[3] for row in store.db.execute('EXPLAIN QUERY PLAN '+query,('signal',30))]
                self.assertTrue(any('events_kind_created' in value for value in plan));self.assertFalse(any('TEMP B-TREE' in value for value in plan))
                self.assertEqual(store.db.execute('SELECT count(*) FROM events').fetchone()[0],2000)
            finally:store.close()
            store=Store(path)
            try:self.assertEqual(store.db.execute("SELECT count(*) FROM sqlite_master WHERE type='index' AND name='events_kind_created'").fetchone()[0],1)
            finally:store.close()

if __name__=='__main__':unittest.main()
