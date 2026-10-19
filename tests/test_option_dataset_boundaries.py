"""Additional adversarial offline dataset checks; synthetic history only."""
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from backtesting.option_dataset import inspect, VERSION

class DatasetBoundaryTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.folder=Path(folder.name);self.path=self.folder/'manifest.json'
        self.now=datetime(2026,10,11,15,tzinfo=timezone.utc)
        base={'provider':'fixture','feed':'SYNTHETIC','data_type':'option_quote',
              'symbol':'SPY261009C00775000','bid':1.,'ask':1.1,'bid_size':2,'ask_size':3}
        self.rows=[{**base,'source_timestamp':'2026-10-06T14:00:00Z','received_timestamp':'2026-10-06T14:00:01Z'},
                   {**base,'source_timestamp':'2026-10-06T14:00:02Z','received_timestamp':'2026-10-06T14:00:03Z'}]
        self.manifest={'schema_version':VERSION,'underlying':'SPY','provider':'fixture','feed':'SYNTHETIC',
                       'source_url':'https://example.invalid/synthetic','retrieved_at':self.now.isoformat(),
                       'data_file':'quotes.jsonl','row_count':2}
    def check(self):
        body='\n'.join(json.dumps(row) for row in self.rows).encode()
        (self.folder/'quotes.jsonl').write_bytes(body)
        self.manifest['sha256']=hashlib.sha256(body).hexdigest()
        self.path.write_text(json.dumps(self.manifest),encoding='utf-8')
        result=inspect(self.path,self.now)
        self.assertFalse(result['live_ready']);self.assertFalse(result['strategy_validated'])
        self.assertEqual(result['action'],'NO TRADE')
        return result

    def test_provider_feed_and_type_mismatch_never_establish_provenance(self):
        for change in ({'provider':'other'},{'feed':'OPRA'},{'data_type':'trade'}):
            with self.subTest(change=change):
                original=self.rows[0].copy();self.rows[0].update(change)
                self.assertIn('QUOTE_PROVENANCE_FIELDS_MISMATCH',self.check()['reasons'])
                self.rows[0]=original

    def test_missing_required_fields_and_nonobject_rows_fail_closed(self):
        original=self.rows[0].copy()
        for field in ('symbol','source_timestamp','received_timestamp','bid_size','ask_size'):
            with self.subTest(field=field):
                self.rows[0]=dict(original);self.rows[0].pop(field)
                self.assertEqual(self.check()['status'],'REJECTED')
        for bad in (None,[],True,'quote'):
            self.rows[0]=bad;self.assertEqual(self.check()['status'],'REJECTED')

    def test_offset_equivalent_timestamps_are_duplicate_quotes(self):
        self.rows[1]['source_timestamp']='2026-10-06T10:00:00-04:00'
        self.assertIn('DUPLICATE_OR_OUT_OF_ORDER_QUOTE',self.check()['reasons'])

    def test_expiration_uses_et_date_without_implying_executable_session(self):
        for index,row in enumerate(self.rows):
            row['source_timestamp']=f'2026-10-10T03:59:0{index}Z'
            row['received_timestamp']=f'2026-10-10T03:59:1{index}Z'
        result=self.check()
        self.assertTrue(result['structural_valid']);self.assertEqual(result['coverage'],'UNVERIFIED')
        self.rows[1]['source_timestamp']='2026-10-10T04:00:00Z'
        self.rows[1]['received_timestamp']='2026-10-10T04:00:01Z'
        self.assertIn('QUOTE_AFTER_EXPIRATION',self.check()['reasons'])

    def test_independent_contract_order_and_zero_bid_are_structural_only(self):
        self.rows[0]['symbol']='SPY261009P00775000'
        self.rows[0]['bid']=0.
        self.rows[1]['source_timestamp']='2026-10-06T13:59:00Z'
        self.rows[1]['received_timestamp']='2026-10-06T13:59:01Z'
        result=self.check()
        self.assertTrue(result['structural_valid']);self.assertEqual(result['contract_count'],2)
        self.assertEqual(result['first_source_timestamp'],'2026-10-06T13:59:00+00:00')
        self.assertEqual(result['status'],'SYNTHETIC_ONLY')

    def test_manifest_count_type_and_future_retrieval_rejected(self):
        for count in (True,2.,'2',None):
            self.manifest['row_count']=count
            self.assertIn('ROW_COUNT_MISMATCH',self.check()['reasons'])
        self.manifest['row_count']=2
        self.manifest['retrieved_at']='2026-10-12T15:00:00Z'
        self.assertIn('FUTURE_RETRIEVAL_TIMESTAMP',self.check()['reasons'])

if __name__=='__main__':unittest.main()
