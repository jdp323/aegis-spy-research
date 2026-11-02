import json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from core.storage import Store
from dashboard.light_snapshot import snapshot
from dashboard.snapshot_cache import recheck,_loader

NOW=datetime(2026,11,2,16,tzinfo=timezone.utc)

class BoundedDashboard(unittest.TestCase):
    def test_query_only_original_timestamps_and_no_private_closure(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);store=Store(root/'runtime/aegis.sqlite')
            old=(NOW-timedelta(minutes=2)).isoformat()
            store.put('research_quote:SPY:iex',{'provider':'alpaca-iex','symbol':'SPY','quality':'DATA_OK','source_timestamp':old,'received_timestamp':old,'payload':{'bid':499,'ask':501,'mid':500}})
            store.put('worker_health',{'at':old,'state':'RUNNING'});store.put('features',{'fixture':'SAVED_COMPLETED_BAR_STATE'})
            before=list(store.db.execute('select key,payload,updated from state order by key'))
            value=snapshot(root,clock=lambda:NOW);value=recheck(value,NOW)
            self.assertEqual(value['research_underlying']['source_timestamp'],old)
            self.assertEqual(value['research_underlying']['quality'],'DATA_STALE')
            self.assertEqual(value['features']['fixture'],'SAVED_COMPLETED_BAR_STATE')
            self.assertIsNone(value['positions']);self.assertFalse(value['LIVE_SIGNAL_READY'])
            self.assertEqual(value['system']['worker']['at'],old)
            after=list(store.db.execute('select key,payload,updated from state order by key'))
            self.assertEqual([tuple(r) for r in before],[tuple(r) for r in after]);store.close()

    def test_missing_database_does_not_create_one_or_invent_data(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);value=snapshot(root,clock=lambda:NOW)
            self.assertFalse((root/'runtime/aegis.sqlite').exists())
            self.assertEqual(value['features'],{});self.assertEqual(value['system']['database'],'UNAVAILABLE')
            self.assertIsNone(value['positions']);self.assertFalse(value['order_execution_enabled'])

    def test_default_http_loader_uses_bounded_reader(self):
        with patch('dashboard.light_snapshot.snapshot',return_value={'fixture':'bounded'}) as reader:
            self.assertEqual(_loader(),{'fixture':'bounded'});reader.assert_called_once_with()

if __name__=='__main__':unittest.main()
