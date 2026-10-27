import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from ops.supervisor import publish_status
class StatusTests(unittest.TestCase):
    def test_stale_service_record_does_not_report_running_from_reused_pid(self):
        from datetime import datetime,timezone,timedelta
        from ops.supervisor import status
        now=datetime(2026,10,27,7,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'runtime').mkdir()
            (root/'runtime/services.json').write_text(json.dumps({'at':(now-timedelta(hours=4)).isoformat(),'components':{'worker':{'state':'RUNNING','pid':123}}}))
            with patch('ops.supervisor.alive',return_value=True):r=status(root,clock=lambda:now,probe=False)
            self.assertEqual(r['components']['worker']['state'],'STALE_STATUS_RECORD');self.assertEqual(r['components']['worker']['reported_state'],'RUNNING')
    def test_children_receive_explicit_installed_runtime_paths(self):
        from ops.supervisor import runtime_environment,PY,NODE
        with patch.dict('os.environ',{},clear=True):
            r=runtime_environment();self.assertEqual(r['AEGIS_PYTHON'],PY);self.assertEqual(r['AEGIS_NODE'],NODE)
    def test_transient_windows_lock_recovers(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'runtime').mkdir();original=Path.replace;calls=[]
            def replace(p,target):
                calls.append(1)
                if len(calls)<3:raise PermissionError('synthetic Windows sharing violation')
                return original(p,target)
            with patch.object(Path,'replace',replace):self.assertTrue(publish_status({'worker':{'state':'RUNNING'}},root,sleep=lambda _:None))
            self.assertEqual(len(calls),3);self.assertEqual(json.loads((root/'runtime/services.json').read_text())['components']['worker']['state'],'RUNNING')
    def test_persistent_lock_preserves_last_good_status_and_does_not_raise(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'runtime').mkdir();target=root/'runtime/services.json';target.write_text('{"previous":true}')
            with patch.object(Path,'replace',side_effect=PermissionError('locked')) as replace:self.assertFalse(publish_status({},root,sleep=lambda _:None));self.assertEqual(replace.call_count,3)
            self.assertEqual(json.loads(target.read_text()),{'previous':True})
            self.assertTrue(publish_status({},root,sleep=lambda _:None))


class StatusObservationClock(unittest.TestCase):
    def test_clock_is_taken_after_file_and_database_reads(self):
        import sqlite3
        from datetime import datetime, timezone, timedelta
        from ops.supervisor import status
        start=datetime(2026,10,20,13,30,tzinfo=timezone.utc)
        observed=start+timedelta(seconds=1)
        clock_value=[start]
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);runtime=root/'runtime';runtime.mkdir()
            services=runtime/'services.json'
            services.write_text(json.dumps({'at':observed.isoformat(),'components':{}}))
            for name in ('telegram_health.json','dispatcher_health.json'):
                (runtime/name).write_text(json.dumps({'at':observed.isoformat(),'state':'RUNNING'}))
            (runtime/'worker_progress.json').write_text(json.dumps({'at':observed.isoformat(),'state':'COMPLETED','last_completed_at':observed.isoformat(),'phase_started_at':observed.isoformat()}))
            db=sqlite3.connect(runtime/'aegis.sqlite')
            db.execute('CREATE TABLE state(key TEXT PRIMARY KEY,payload TEXT)')
            db.execute('INSERT INTO state VALUES(?,?)',('worker_health',json.dumps({'at':observed.isoformat(),'state':'RUNNING'})))
            db.commit();db.close()
            before={p.name:p.read_bytes() for p in runtime.iterdir()}
            read=Path.read_text;service_reads=[]
            def advancing_read(path,*args,**kwargs):
                value=read(path,*args,**kwargs)
                if path==services:service_reads.append(path)
                if path.name=='worker_progress.json':clock_value[0]=start+timedelta(seconds=2)
                return value
            with patch.object(Path,'read_text',advancing_read),patch('ops.supervisor.start') as launch,patch('ops.supervisor.run') as run:
                result=status(root,clock=lambda:clock_value[0],probe=False)
                launch.assert_not_called();run.assert_not_called()
            self.assertEqual(result['at'],(start+timedelta(seconds=2)).isoformat())
            self.assertEqual(len(service_reads),1)
            for name in ('supervisor','listener','dispatcher'):
                self.assertEqual(result['heartbeats'][name]['age_seconds'],1)
            worker=result['heartbeats']['worker']
            self.assertEqual(worker['completed_work_age_seconds'],1)
            self.assertEqual(worker['active_phase_age_seconds'],1)
            self.assertEqual(worker['cycle']['age_seconds'],1)
            self.assertEqual(before,{p.name:p.read_bytes() for p in runtime.iterdir()})
    def test_genuinely_future_heartbeat_stays_signed(self):
        from datetime import datetime,timezone,timedelta
        from ops.supervisor import status
        now=datetime(2026,10,20,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'runtime').mkdir()
            (root/'runtime/services.json').write_text(json.dumps({'at':(now+timedelta(seconds=2)).isoformat(),'components':{}}))
            result=status(root,clock=lambda:now,probe=False)
            self.assertEqual(result['heartbeats']['supervisor']['age_seconds'],-2)
            self.assertFalse(result['LIVE_SIGNAL_READY'])
    def test_missing_or_malformed_time_remains_unavailable(self):
        from datetime import datetime,timezone
        from ops.supervisor import status
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'runtime').mkdir()
            (root/'runtime/services.json').write_text(json.dumps({'at':'invalid','components':{}}))
            result=status(root,clock=lambda:datetime(2026,10,20,tzinfo=timezone.utc),probe=False)
            self.assertIsNone(result['heartbeats']['supervisor']['age_seconds'])
            self.assertIsNone(result['heartbeats']['listener']['age_seconds'])
            self.assertIsNone(result['heartbeats']['worker']['completed_work_age_seconds'])

    def test_clock_is_taken_after_bounded_http_probe(self):
        from datetime import datetime,timezone,timedelta
        from unittest.mock import MagicMock
        from ops.supervisor import status
        start=datetime(2026,10,20,tzinfo=timezone.utc);clock_value=[start]
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'runtime').mkdir()
            (root/'runtime/services.json').write_text(json.dumps({'at':(start+timedelta(seconds=1)).isoformat(),'components':{}}))
            response=MagicMock();response.status=200;response.read.return_value=b'{}'
            response.__enter__.return_value=response
            def probe(*args,**kwargs):
                clock_value[0]=start+timedelta(seconds=2)
                return response
            with patch('urllib.request.urlopen',side_effect=probe) as request:
                result=status(root,clock=lambda:clock_value[0])
            self.assertEqual(result['heartbeats']['supervisor']['age_seconds'],1)
            self.assertEqual(result['at'],clock_value[0].isoformat())
            self.assertEqual(result['dashboard_http'],200)
            request.assert_called_once_with('http://127.0.0.1:8767/healthz',timeout=2)
            response.read.assert_called_once_with(4096)
