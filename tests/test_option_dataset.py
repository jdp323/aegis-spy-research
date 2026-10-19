import hashlib,json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone
from backtesting.option_dataset import inspect,VERSION

class OptionDatasetTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.root=Path(self.folder.name);self.path=self.root/'manifest.json'
        self.now=datetime(2026,10,6,15,tzinfo=timezone.utc)
        base={'provider':'fixture','feed':'SYNTHETIC','data_type':'option_quote','symbol':'SPY261009C00775000','bid':1.0,'ask':1.1,'bid_size':3,'ask_size':4}
        self.rows=[{**base,'source_timestamp':'2026-10-06T14:00:00+00:00','received_timestamp':'2026-10-06T14:00:01+00:00'},{**base,'source_timestamp':'2026-10-06T14:00:02+00:00','received_timestamp':'2026-10-06T14:00:03+00:00'}]
        self.manifest={'schema_version':VERSION,'underlying':'SPY','provider':'fixture','feed':'SYNTHETIC','source_url':'https://example.invalid/synthetic','retrieved_at':self.now.isoformat(),'data_file':'quotes.jsonl','row_count':2}
    def save(self):
        body='\n'.join(json.dumps(r) for r in self.rows).encode()
        (self.root/'quotes.jsonl').write_bytes(body);self.manifest['sha256']=hashlib.sha256(body).hexdigest();self.path.write_text(json.dumps(self.manifest))
    def check(self):self.save();return inspect(self.path,self.now)
    def test_missing_dataset_fail_closed(self):
        result=inspect(self.path,self.now);self.assertEqual(result['status'],'UNAVAILABLE');self.assertFalse(result['live_ready'])
    def test_synthetic_not_live_or_strategy_evidence(self):
        result=self.check();self.assertTrue(result['structural_valid']);self.assertEqual(result['status'],'SYNTHETIC_ONLY');self.assertEqual(result['quote_rows'],2);self.assertEqual(result['action'],'NO TRADE');self.assertFalse(result['strategy_validated'])
    def test_manifest_opra_claim_is_not_independent_provenance(self):
        self.manifest['feed']='OPRA'
        for row in self.rows:row['feed']='OPRA'
        result=self.check();self.assertEqual(result['status'],'STRUCTURALLY_INSPECTED_ONLY');self.assertEqual(result['provenance'],'UNVERIFIED');self.assertFalse(result['live_ready'])
    def test_indicative_and_underlying_data_rejected(self):
        self.manifest['feed']='INDICATIVE';self.assertEqual(self.check()['status'],'REJECTED')
        self.manifest['feed']='SYNTHETIC';self.rows[0]['symbol']='SPY';self.assertEqual(self.check()['status'],'REJECTED')
    def test_tampered_data_rejected(self):
        self.save();(self.root/'quotes.jsonl').write_text('[]');self.assertIn('DATASET_HASH_MISMATCH',inspect(self.path,self.now)['reasons'])
    def test_unsafe_path_and_credential_url_rejected(self):
        for name in ('../quotes.jsonl','C:/quotes.jsonl','quotes:alternate.jsonl'):
            self.manifest['data_file']=name;self.assertEqual(self.check()['status'],'REJECTED')
        self.manifest['data_file']='quotes.jsonl';self.manifest['source_url']='https://example.invalid/quotes?api_key=fixture';self.assertEqual(self.check()['status'],'REJECTED')
    def test_crossed_nonfinite_and_invalid_sizes_rejected(self):
        for change in ({'bid':2},{'ask':float('nan')},{'bid':-1},{'bid_size':True},{'ask_size':-1}):
            with self.subTest(change=change):
                old=self.rows[0].copy();self.rows[0].update(change);self.assertEqual(self.check()['status'],'REJECTED');self.rows[0]=old
    def test_duplicate_out_of_order_and_invalid_timestamps_rejected(self):
        for change in ({'source_timestamp':self.rows[0]['source_timestamp']},{'received_timestamp':'2026-10-06T13:59:00Z'},{'source_timestamp':'2026-10-06T14:00:02'},{'received_timestamp':'2026-10-06T16:00:00Z'}):
            with self.subTest(change=change):
                old=self.rows[1].copy();self.rows[1].update(change);self.assertEqual(self.check()['status'],'REJECTED');self.rows[1]=old
    def test_expiration_row_count_and_empty_history_rejected(self):
        self.rows[0]['symbol']='SPY261005C00775000';self.assertEqual(self.check()['status'],'REJECTED')
        self.rows[0]['symbol']='SPY261009C00775000';self.manifest['row_count']=999;self.assertEqual(self.check()['status'],'REJECTED')
        self.rows=[];self.manifest['row_count']=0;self.assertEqual(self.check()['status'],'REJECTED')

if __name__=='__main__':unittest.main()
