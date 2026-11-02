import copy,json,tempfile,threading,time,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from core.fast_path import FastPath,InputStore,feature_key,feature_get,feature_put,phase_times,public_evaluation_due
from core.storage import Store
from backtesting.idea_tracker import IdeaTracker


class FreeFastPathTests(unittest.TestCase):
    def test_all_session_slots_continue_and_closed_unresolved_plans_are_not_abandoned(self):
        from zoneinfo import ZoneInfo
        class State:
            def get(self,key,default=None):return ['retired'] if key=='primary-admin-closures:v1' else default
        class Tracker:
            rows=[]
            def positions(self,active_only=False):return self.rows
        store=State();tracker=Tracker();et=ZoneInfo('America/New_York')
        for hour,minute in ((9,15),(9,20),(9,45),(10,0),(15,45),(16,15),(16,20)):
            self.assertTrue(public_evaluation_due(store,tracker,datetime(2026,11,2,hour,minute,tzinfo=et)))
        sunday=datetime(2026,11,1,18,tzinfo=et)
        self.assertFalse(public_evaluation_due(store,tracker,sunday))
        tracker.rows=[{'signal_id':'silent','alerted':False}];self.assertFalse(public_evaluation_due(store,tracker,sunday))
        tracker.rows=[{'signal_id':'unresolved','alerted':True}];self.assertTrue(public_evaluation_due(store,tracker,sunday))
        tracker.rows=[{'signal_id':'retired','alerted':True}];self.assertFalse(public_evaluation_due(store,tracker,sunday))
        self.assertTrue(public_evaluation_due(store,tracker,datetime(2026,11,27,13,15,tzinfo=et)))
        self.assertFalse(public_evaluation_due(store,tracker,datetime(2026,11,27,13,21,tzinfo=et)))
    def test_independent_timer_progresses_during_blocked_maintenance_and_owns_connection(self):
        with tempfile.TemporaryDirectory() as d:
            calls=[];event=threading.Event();main=threading.get_ident()
            def callback(store,now):
                store.put('fixture-current',{'at':now.isoformat()});calls.append(threading.get_ident());event.set();return {'live_ready':False}
            runner=FastPath(d,callback,interval=.1);self.assertTrue(runner.start());self.assertTrue(event.wait(3));self.assertFalse(runner.start())
            time.sleep(.15);self.assertTrue(runner.health()['thread_alive']);self.assertNotEqual(calls[0],main)
            result=runner.close(3);self.assertFalse(result['thread_alive']);self.assertEqual(result['state'],'STOPPED')
            db=Store(Path(d)/'runtime/aegis.sqlite');self.assertIsNotNone(db.get('fixture-current'));db.close()

    def test_failure_is_preserved_and_timer_keeps_progress(self):
        with tempfile.TemporaryDirectory() as d:
            count=[0];done=threading.Event()
            def callback(store,now):
                count[0]+=1
                if count[0]==1:raise ValueError('secret-must-not-be-exported')
                done.set();return {'completed':True}
            runner=FastPath(d,callback,interval=.1);runner.start()
            # A changed input forces a subsequent check without waiting five seconds.
            self.assertTrue(runner.ready.wait(3));time.sleep(.1)
            store=Store(Path(d)/'runtime/aegis.sqlite');store.put('quote:SPY',{'fixture':True});store.close()
            self.assertTrue(done.wait(3));runner.close(3);self.assertGreaterEqual(count[0],2)
            self.assertNotIn('secret-must-not-be-exported',json.dumps(runner.health()))

    def test_cache_revision_is_coherent_and_fresh_clock_remains_in_key(self):
        with tempfile.TemporaryDirectory() as d:
            store=InputStore(Path(d)/'s.sqlite');other=Store(Path(d)/'s.sqlite');now=datetime.now(timezone.utc)
            try:
                store.put('bars',{'value':1});store.snapshot(['bars']);key=feature_key(store,'fixture',['bars'],now)
                feature_put(store,key,{'values':[1]});value=feature_get(store,key);value['values'].append(2)
                self.assertEqual(feature_get(store,key),{'values':[1]})
                other.put('bars',{'value':2});self.assertEqual(feature_key(store,'fixture',['bars'],now),key)
                store.snapshot(['bars']);self.assertNotEqual(feature_key(store,'fixture',['bars'],now),key)
                self.assertNotEqual(feature_key(store,'fixture',['bars'],now+timedelta(minutes=1)),feature_key(store,'fixture',['bars'],now))
            finally:store.close();other.close()

    def test_projection_preserves_events_and_external_appends_across_restart(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'i.sqlite';t=IdeaTracker(path);now=datetime.now(timezone.utc)
            row={'signal_id':'a'*24,'status':'OPEN','feed_quality':'IEX'}
            t.append(row,'REGISTER',now);other=IdeaTracker(path);other.append(dict(row,status='CLOSED'),'OBSERVE',now+timedelta(seconds=1));other.close()
            self.assertEqual(t.positions(active_only=True),[]);self.assertEqual(t.positions()[0]['status'],'CLOSED')
            self.assertEqual(t.db.execute('select count(*) from idea_events').fetchone()[0],2);t.close()
            t=IdeaTracker(path);self.assertEqual(t.positions()[0]['status'],'CLOSED');t.close()

    def test_actual_intervals_are_separate_and_not_fabricated_decode_or_network_latency(self):
        now=datetime.now(timezone.utc);q={'source_timestamp':(now-timedelta(seconds=7)).isoformat(),'received_timestamp':(now-timedelta(seconds=2)).isoformat()}
        m=phase_times(q,now,.1);self.assertEqual(m['source_to_receipt_seconds'],5);self.assertEqual(m['receipt_to_decision_seconds'],2)
        self.assertIsNone(m['decode_seconds']);self.assertIsNone(m['queue_seconds'])


if __name__=='__main__':unittest.main()
