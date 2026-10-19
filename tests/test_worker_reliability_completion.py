"""Isolated reliability regressions: fake networks, no production ledgers/sends."""
import json
import sqlite3
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

from core.background_jobs import Jobs, Phases
from core.storage import Store
from data.backfill import BackgroundBackfill, history
from data.providers import AlpacaProvider, UnconfiguredProvider

NOW = datetime(2026, 10, 16, 15, 0, tzinfo=timezone.utc)


class JobTests(unittest.TestCase):
    def test_blocked_network_does_not_block_submit_or_owner_apply(self):
        gate = threading.Event(); started = threading.Event(); applied = []
        jobs = Jobs(maximum=1)
        def work():
            started.set();gate.wait(3);return {'source_timestamp':NOW.isoformat()}
        self.assertTrue(jobs.submit('history',work,applied.append,1))
        self.assertTrue(started.wait(1));self.assertFalse(jobs.submit('history',lambda:None))
        self.assertFalse(jobs.submit('rss',lambda:None));self.assertEqual(jobs.drain(),[])
        self.assertEqual(applied,[])
        gate.set()
        for _ in range(100):
            result=jobs.drain()
            if result:break
            time.sleep(.005)
        self.assertEqual(result[0]['state'],'COMPLETED')
        self.assertEqual(applied,[{'source_timestamp':NOW.isoformat()}]);self.assertEqual(jobs.health()['active_jobs'],[])
        self.assertTrue(jobs.submit('rss',lambda:None));jobs.close()

    def test_over_budget_thread_is_not_claimed_canceled(self):
        gate=threading.Event(); clock=[0.];jobs=Jobs(clock=lambda:clock[0])
        jobs.submit('history',lambda:gate.wait(3),budget=1);clock[0]=2
        health=jobs.health()['active_jobs'][0]
        self.assertEqual(health['state'],'RUNNING_OVER_BUDGET');self.assertTrue(health['thread_alive'])
        gate.set();jobs.close()

    def test_failed_job_never_exports_exception_text_or_applies_value(self):
        jobs=Jobs();applied=[]
        def fail():raise OSError('private-provider-secret-body')
        jobs.submit('rss',fail,applied.append)
        for _ in range(100):
            result=jobs.drain()
            if result:break
            time.sleep(.005)
        self.assertEqual(result[0]['state'],'FAILED');self.assertEqual(result[0]['error_type'],'OSError')
        self.assertNotIn('private-provider-secret-body',json.dumps(result));self.assertEqual(applied,[]);jobs.close()

    def test_closed_jobs_refuse_new_work(self):
        jobs=Jobs();jobs.close();self.assertFalse(jobs.submit('rss',lambda:None))


class PhaseTests(unittest.TestCase):
    def test_phase_failure_records_exact_phase_code_and_signed_clock_difference(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);clock=[10.];wall=[NOW];phases=Phases(root,clock=lambda:clock[0],wall=lambda:wall[0])
            phases.start('history_apply',1);clock[0]=12;wall[0]=NOW+timedelta(seconds=3)
            try:
                db=sqlite3.connect(':memory:');db.execute('SELECT * FROM missing_fixture')
            except sqlite3.OperationalError as error:phases.finish(error)
            finally:db.close()
            row=phases.summary()['recent_phases'][-1]
            self.assertEqual(row['phase'],'history_apply');self.assertEqual(row['state'],'FAILED')
            self.assertEqual(row['sqlite_errorname'],'SQLITE_ERROR');self.assertEqual(row['wall_minus_monotonic_seconds'],1)
            self.assertTrue(row['deadline_missed']);self.assertIsNone(phases.last_completed_at)
            published=json.loads((root/'runtime/worker_progress.json').read_text())
            self.assertEqual(published['phase'],'history_apply');self.assertNotIn('missing_fixture',json.dumps(published))

    def test_phase_log_is_append_only_and_progress_is_distinct_from_completed_work(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=Phases(root);p.start('cycle_inputs');p.start('position_review')
            row=json.loads((root/'runtime/worker_progress.json').read_text())
            self.assertEqual(row['state'],'RUNNING_PHASE');self.assertIsNotNone(row['last_completed_at'])
            p.finish();self.assertEqual(sum(len(path.read_text().splitlines()) for path in root.joinpath('logs/worker_phases').glob('*.jsonl')),2)
            self.assertEqual(p.summary()['recent_phases'][-1]['phase'],'position_review')


class DatabaseRetryTests(unittest.TestCase):
    def test_busy_retries_are_bounded_and_preserve_committed_rows(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'fixture.sqlite';s=Store(path,lock_timeout=.01,retry_attempts=3,sleep=lambda _:None)
            s.put('before',{'value':1});other=sqlite3.connect(path);other.execute('BEGIN IMMEDIATE')
            try:
                with self.assertRaises(sqlite3.OperationalError):s.put('blocked',{})
                self.assertEqual(s.metrics['busy_retries'],2);self.assertEqual(s.metrics['failures'],1)
                self.assertIsNone(s.get('blocked'));self.assertEqual(s.get('before'),{'value':1})
            finally:other.rollback();other.close()
            s.put('recovered',{});self.assertEqual(s.get('recovered'),{});s.close()

    def test_only_busy_errors_retry_not_syntax_or_integrity(self):
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d)/'fixture.sqlite',sleep=lambda _:self.fail('non-busy error retried'))
            with self.assertRaises(sqlite3.OperationalError):s.transaction(lambda:s.db.execute('SELECT * FROM missing_fixture'))
            self.assertEqual(s.metrics['busy_retries'],0);self.assertEqual(s.metrics['failures'],1);s.close()

    def test_lock_recovery_within_bound_and_audit_hash_chain(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'fixture.sqlite';s=Store(path,lock_timeout=.01);other=sqlite3.connect(path);other.execute('BEGIN IMMEDIATE')
            s.sleep=lambda _:other.rollback()
            s.audit('one','fixture','test',{});s.audit('one','fixture','test',{});s.audit('two','fixture','test',{})
            rows=s.db.execute('SELECT previous,hash FROM audit ORDER BY seq').fetchall()
            self.assertEqual(len(rows),2);self.assertEqual(rows[0]['previous'],'GENESIS');self.assertEqual(rows[1]['previous'],rows[0]['hash'])
            self.assertEqual(s.metrics['busy_retries'],1);other.close();s.close()

    def test_atomic_history_precedence_and_concurrent_merges_keep_both_writers(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'fixture.sqlite';s=Store(path)
            stream={'t':NOW.isoformat(),'c':500,'source':'STREAM'}
            s.merge_rows('history',[stream],incoming_wins=True)
            s.merge_rows('history',[dict(stream,c=400,source='REST_BACKFILL')])
            self.assertEqual(s.get('history'),[stream])
            s.merge_rows('history',[dict(stream,c=501)],incoming_wins=True)
            self.assertEqual(s.get('history')[0]['c'],501);s.close()
            barrier=threading.Barrier(2);failures=[]
            def writer(offset):
                own=Store(path)
                try:
                    barrier.wait(timeout=3)
                    own.merge_rows('history',[{'t':(NOW+timedelta(minutes=offset+i)).isoformat(),'c':500} for i in range(10)],incoming_wins=True)
                except Exception as error:failures.append(type(error).__name__)
                finally:own.close()
            threads=[threading.Thread(target=writer,args=(offset,)) for offset in (1,11)]
            for thread in threads:thread.start()
            for thread in threads:thread.join(timeout=5)
            self.assertFalse(any(thread.is_alive() for thread in threads));self.assertEqual(failures,[])
            s=Store(path);self.assertEqual(len(s.get('history')),21);s.close()

    def test_equivalent_aware_offsets_are_one_history_minute(self):
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d)/'fixture.sqlite')
            s.merge_rows('history',[{'t':NOW.isoformat(),'c':500}])
            s.merge_rows('history',[{'t':NOW.astimezone(timezone(timedelta(hours=-4))).isoformat(),'c':501}],incoming_wins=True)
            self.assertEqual(len(s.get('history')),1);self.assertEqual(s.get('history')[0]['c'],501);s.close()


class WorkerTests(unittest.TestCase):
    def test_background_cycle_reaches_reviews_while_history_network_waits(self):
        from core.upgrade_service import Engine
        from core.storage import ROOT
        from core.sessions import market_session
        gate=threading.Event();started=threading.Event();network_completions=[]
        def provider_request(path,params):
            if path.endswith('/bars'):
                started.set();released=gate.wait(30);network_completions.append(released);return {'bars':[]}
            return {'quote':{},'snapshots':{}}
        class Fixed(datetime):
            @classmethod
            def now(cls,tz=None):return NOW
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'config').mkdir();(root/'monitoring').mkdir()
            config=json.loads((ROOT/'config/upgrade.json').read_text());config['idea_engine_enabled']=False
            (root/'config/upgrade.json').write_text(json.dumps(config));s=Store(root/'runtime/aegis.sqlite')
            s.put('ntp_clock',{'at':NOW.isoformat(),'offset_seconds':0,'state':'MEASURED'})
            with patch('core.upgrade_service.ROOT',root),patch('core.upgrade_service.books',return_value={}),patch('core.upgrade_service.datetime',Fixed):
                engine=Engine(s,AlpacaProvider(provider_request),background=True);engine.reliability.clock=lambda:NOW
                engine.last_phase=market_session(NOW)['state']
                for key in ('news_headlines','market_news','reddit_sentiment','calendar','history_sample'):engine.due[key]=float('inf')
                try:
                    result=engine.tick()
                    self.assertTrue(started.wait(2));self.assertFalse(gate.is_set());self.assertEqual(network_completions,[])
                    self.assertEqual(result['action'],'NO TRADE');self.assertEqual(s.get('worker_health')['state'],'RUNNING')
                    names={r['phase'] for r in s.get('worker_health')['phases']['recent_phases']}
                    self.assertIn('reported_position_reviews',names);self.assertIn('legacy_analysis',names)
                    self.assertFalse(s.get('latest_evaluation')['live_signal_ready'])
                finally:gate.set();engine.close()

    def test_injected_worker_keeps_deterministic_foreground_default(self):
        from core.upgrade_service import Engine
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);s=Store(root/'runtime/aegis.sqlite')
            with patch('core.upgrade_service.ROOT',root):engine=Engine(s,UnconfiguredProvider())
            self.assertFalse(engine.background);applied=[];engine.collect('fixture',lambda:7,applied.append)
            self.assertEqual(applied,[7]);engine.close()

    def test_older_or_invalid_background_quote_cannot_replace_newer_stream_snapshot(self):
        from core.upgrade_service import Engine
        from data.models import quote
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);s=Store(root/'runtime/aegis.sqlite')
            with patch('core.upgrade_service.ROOT',root):engine=Engine(s,UnconfiguredProvider())
            new=quote('alpaca-sip','SPY',{'t':NOW.isoformat(),'bp':500,'ap':501},received=NOW.isoformat()).view(NOW)
            s.put('quote:SPY',new)
            old=quote('alpaca-sip','SPY',{'t':(NOW-timedelta(seconds=1)).isoformat(),'bp':400,'ap':401},received=NOW.isoformat()).view(NOW)
            engine.market_result('quote:SPY',old);engine.market_result('quote:SPY',{'quality':'DATA_INVALID'})
            self.assertEqual(s.get('quote:SPY'),new);engine.close()

    def test_real_background_history_has_separate_database_and_does_not_wait(self):
        from data.models import Quality
        gate=threading.Event();started=threading.Event()
        def transport(path,p):
            started.set();gate.wait(30)
            return {'bars':[]}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);s=Store(root/'runtime/aegis.sqlite');service=BackgroundBackfill(root/'runtime/observability.sqlite',s.path,AlpacaProvider(transport))
            try:
                service.tick(s,NOW)
                self.assertTrue(started.wait(3));s.put('analysis_during_history',{'quality':Quality.INCOMPLETE})
                self.assertFalse(gate.is_set());self.assertEqual(service.health()['state'],'RUNNING')
                self.assertFalse(service.health()['analysis_blocked']);self.assertEqual(s.get('analysis_during_history')['quality'],Quality.INCOMPLETE)
            finally:gate.set();service.close();s.close()

    def test_partial_history_after_deadline_never_becomes_confirmed_coverage(self):
        row={'t':NOW.isoformat(),'o':500,'h':501,'l':499,'c':500,'v':1}
        class Provider:
            def get(self,*args):return {'bars':[row],'next_page_token':'more'}
        p=Provider()
        with patch('data.backfill.time.monotonic',side_effect=[0,1,61]):
            with self.assertRaisesRegex(ValueError,'HISTORY_DEADLINE_EXCEEDED'):history(p,NOW-timedelta(minutes=1),NOW)

    def test_parent_event_id_preserved_in_atomic_outbox(self):
        from core.upgrade_service import enqueue
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'monitoring').mkdir();s=Store(root/'runtime/aegis.sqlite')
            with patch('core.upgrade_service.ROOT',root):enqueue(s,'child-fixture','EXAMPLE',parent_event_id='parent-fixture')
            row=json.loads((root/'monitoring/outbox/child-fixture.json').read_text())
            self.assertEqual(row['parent_event_id'],'parent-fixture');s.close()

    def test_read_only_service_health_distinguishes_phase_start_from_completed_work(self):
        from ops.supervisor import status
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);s=Store(root/'runtime/aegis.sqlite')
            s.put('worker_health',{'at':(NOW-timedelta(seconds=5)).isoformat(),'state':'RUNNING','cycle_seconds':2,'database':s.metrics,'private_reported_positions':['do-not-expose']});s.close()
            progress=root/'runtime/worker_progress.json'
            progress.write_text(json.dumps({'at':NOW.isoformat(),'state':'RUNNING_PHASE','phase':'reported_position_reviews','phase_started_at':(NOW-timedelta(seconds=2)).isoformat(),'last_completed_at':(NOW-timedelta(seconds=10)).isoformat()}))
            before={p.name:p.read_bytes() for p in root.joinpath('runtime').iterdir() if p.is_file() and not p.name.endswith(('-wal','-shm'))}
            result=status(root,clock=lambda:NOW,probe=False)
            after={p.name:p.read_bytes() for p in root.joinpath('runtime').iterdir() if p.is_file() and not p.name.endswith(('-wal','-shm'))}
            worker=result['heartbeats']['worker'];self.assertEqual(worker['active_phase_age_seconds'],2);self.assertEqual(worker['completed_work_age_seconds'],10);self.assertEqual(worker['cycle']['age_seconds'],5)
            self.assertNotIn('do-not-expose',json.dumps(result));self.assertTrue(result['read_only']);self.assertEqual(before,after)


class PrivateMonitoringTests(unittest.TestCase):
    def test_tenant_incident_bypasses_research_cap_deduplicates_and_never_closes(self):
        from core.upgrade_service import position_monitoring_incident
        from ops.day_simulation import MemoryStore
        from data.models import quote
        store=MemoryStore();sent=[];tenant='fixture-guest';p={'contract':'SPY261023C00500000','quantity':1,'cost_usd':'200.65'}
        store.put('paper_notifications:2026-10-16',{'count':999})
        def publish(*args,**kwargs):sent.append((args,kwargs))
        self.assertEqual(position_monitoring_incident(store,p,{},None,NOW,tenant,publish),'WARNING')
        self.assertEqual(position_monitoring_incident(store,p,{},None,NOW+timedelta(seconds=1),tenant,publish),'UNCHANGED')
        self.assertEqual(len(sent),1);self.assertEqual(sent[0][0][3:5],('PRIVATE',tenant));self.assertIn('No exit or closure inferred',sent[0][0][2]);self.assertEqual(p['quantity'],1)
        after=NOW+timedelta(seconds=2)
        uq=quote('alpaca-iex','SPY',{'t':after.isoformat(),'bp':500,'ap':501},received=after.isoformat()).view(after)
        oq=quote('alpaca-opra',p['contract'],{'t':after.isoformat(),'bp':2,'ap':2.1},received=after.isoformat()).view(after)
        self.assertEqual(position_monitoring_incident(store,p,uq,oq,after,tenant,publish),'RECOVERY')
        self.assertEqual(len(sent),2);self.assertEqual(sent[1][1]['alert_type'],'POSITION_MONITORING_RECOVERY')
        self.assertEqual(position_monitoring_incident(store,p,uq,oq,after,tenant,publish),'UNCHANGED');self.assertEqual(len(sent),2)

    def test_review_gap_does_not_recover_on_the_same_resume_read(self):
        from core.upgrade_service import position_monitoring_incident
        from ops.day_simulation import MemoryStore
        from data.models import quote
        s=MemoryStore();sent=[];p={'contract':'SPY261023C00500000','quantity':1,'cost_usd':'200'}
        def quotes(t):return (quote('alpaca-iex','SPY',{'t':t.isoformat(),'bp':500,'ap':501},received=t.isoformat()).view(t),quote('alpaca-opra',p['contract'],{'t':t.isoformat(),'bp':2,'ap':2.1},received=t.isoformat()).view(t))
        def publish(*args,**kwargs):sent.append((args,kwargs))
        uq,oq=quotes(NOW);self.assertEqual(position_monitoring_incident(s,p,uq,oq,NOW,'owner',publish),'UNCHANGED')
        later=NOW+timedelta(seconds=61);uq,oq=quotes(later)
        self.assertEqual(position_monitoring_incident(s,p,uq,oq,later,'owner',publish),'WARNING');self.assertIn('REVIEW_GAP_OR_CLOCK_JUMP',sent[0][0][2])
        self.assertEqual(position_monitoring_incident(s,p,uq,oq,later+timedelta(seconds=1),'owner',publish),'RECOVERY')

    def test_reported_book_removal_resets_incident_without_claiming_an_exit(self):
        from core.upgrade_service import reconcile_monitoring_holdings,position_monitoring_incident
        from ops.day_simulation import MemoryStore
        s=MemoryStore();sent=[];p={'contract':'SPY261023C00500000','quantity':1,'cost_usd':'200'}
        def publish(*args,**kwargs):sent.append((args,kwargs))
        reconcile_monitoring_holdings(s,{'owner':[p]},NOW);position_monitoring_incident(s,p,{},None,NOW,'owner',publish)
        reconcile_monitoring_holdings(s,{},NOW+timedelta(seconds=1));self.assertEqual(len(sent),1)
        reconcile_monitoring_holdings(s,{'owner':[p]},NOW+timedelta(seconds=2));self.assertEqual(position_monitoring_incident(s,p,{},None,NOW+timedelta(seconds=2),'owner',publish),'WARNING');self.assertEqual(len(sent),2)


if __name__=='__main__':unittest.main()
