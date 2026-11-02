import json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from data.free_quote_recorder import QuoteRecorder
from data.models import quote

class QuoteRecorderTests(unittest.TestCase):
    def test_prospective_quote_keeps_original_source_and_receipt(self):
        now=datetime.now(timezone.utc);source=now-timedelta(seconds=14)
        q=quote('alpaca-iex','SPY',{'bp':500,'ap':500.01,'t':source.isoformat()},received=now.isoformat()).view(now)
        with tempfile.TemporaryDirectory() as d:
            r=QuoteRecorder(d);self.assertTrue(r.offer(q));h=r.close(3);self.assertEqual(h['written'],1);self.assertEqual(h['write_failures'],0)
            files=list((Path(d)/'logs/market_capture').glob('*/iex_bbo.jsonl'));row=json.loads(files[0].read_text());self.assertEqual(row['source_at'],source.isoformat());self.assertEqual(row['received_at'],now.isoformat());self.assertFalse(row['option_quote'])
    def test_other_feed_and_simulated_quote_do_not_become_iex_history(self):
        now=datetime.now(timezone.utc);q=quote('alpaca-sip','SPY',{'bp':500,'ap':500.01,'t':now.isoformat()}).view(now)
        with tempfile.TemporaryDirectory() as d:
            r=QuoteRecorder(d);self.assertFalse(r.offer(q));q['feed_quality']='SIMULATED'
            with self.assertRaises(ValueError):r.offer(q)
            self.assertEqual(r.close(3)['written'],0)

if __name__=='__main__':unittest.main()
