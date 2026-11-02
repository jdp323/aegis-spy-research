"""Isolated clock fixtures: no network, receipts or production databases."""
import tempfile, unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from core.storage import Store
from core.v6_service import monitor_checks


class IndependentOwnerChecks(unittest.TestCase):
    def test_precheck_and_outage_restart_deduplication_without_maintenance(self):
        now=datetime(2026,11,2,14,20,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); path=root/'runtime/aegis.sqlite';store=Store(path);messages=[]
            def enqueue(*args,**kwargs):messages.append((args[1],kwargs))
            monitor_checks(store,now,enqueue,root,now-timedelta(minutes=3))
            self.assertEqual(len(messages),2)
            self.assertIsNotNone(store.get('v6-precheck:2026-11-02'))
            self.assertIsNotNone(store.get('v6-outage:2026-11-02'))
            self.assertTrue(all(x[1]['kind']=='RESEARCH' for x in messages))
            store.close();store=Store(path)
            monitor_checks(store,now+timedelta(seconds=5),enqueue,root,now)
            self.assertEqual(len(messages),2)
            store.put('last_market:iex',{'received_timestamp':'MALFORMED_FIXTURE'})
            monitor_checks(store,now+timedelta(seconds=5),enqueue,root,now)
            self.assertEqual(len(messages),2)
            store.put('last_market:iex',{'received_timestamp':(now+timedelta(seconds=5)).isoformat()})
            monitor_checks(store,now+timedelta(seconds=6),enqueue,root,now)
            self.assertEqual(len(messages),3)
            self.assertEqual(messages[-1][1]['alert_type'],'DATA_RECOVERY')
            self.assertIsNone(store.get('v6-outage:2026-11-02'));store.close()

    def test_closed_session_does_not_replay_old_selfcheck_or_warn(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);store=Store(root/'runtime/aegis.sqlite');messages=[]
            now=datetime(2026,11,1,22,tzinfo=timezone.utc)
            monitor_checks(store,now,lambda *a,**k:messages.append(a),root,now-timedelta(days=2))
            self.assertEqual(messages,[]);store.close()


if __name__=='__main__':unittest.main()
