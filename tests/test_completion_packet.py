import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from ops.completion_verification import extend, latest_session, compact_historical_duplicates


class CompletionPacketTests(unittest.TestCase):
    def test_newer_run_tests_result_is_not_replaced_with_old_saved_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'research/completion_verification/final';folder.mkdir(parents=True)
            (folder/'latest_tests.json').write_text(json.dumps({'checked_at':'2026-10-17T16:00:00+00:00','successful':True,'fixture':'older'}))
            packet={'header':{},'tests':{'checked_at':'2026-10-18T16:00:00+00:00','successful':False,'fixture':'newer_failure'}}
            extend(packet,root,datetime(2026,10,18,17,tzinfo=timezone.utc))
            self.assertEqual(packet['tests']['fixture'],'newer_failure')
            self.assertFalse(packet['tests']['successful'])

    def test_latest_saved_session_preserves_generation_time_and_holiday_exclusion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);reports=root/'daily_reports';reports.mkdir()
            good={'date_et':'2026-10-16','generated_at_utc':'2026-10-17T16:24:00+00:00','status':'PASS','minute_coverage':[{'hour_et':'09','recorded':30}],'LIVE_SIGNAL_READY':False}
            (reports/'SESSION_REPORT_2026-10-16.json').write_text(json.dumps(good))
            (reports/'SESSION_REPORT_2026-10-17.json').write_text(json.dumps({'date_et':'2026-10-17','status':'NO_SESSION'}))
            result=latest_session(root,datetime(2026,10,18,16,tzinfo=timezone.utc))
            self.assertEqual(result['date_et'],'2026-10-16')
            self.assertEqual(result['saved_report_generated_at_utc'],good['generated_at_utc'])
            self.assertEqual(result['report']['minute_coverage'],good['minute_coverage'])
            self.assertIn('sha256',result['artifact'])

    def test_compaction_cannot_hide_secret_and_labels_old_session_historical(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            packet={'v5':{},'v6':{'last_session':{'date_et':'2026-10-09'}},'samples_EXAMPLE':{},'gaps':{}}
            compact_historical_duplicates(packet,root,None,None)
            self.assertNotIn('last_session',packet['v6'])
            self.assertEqual(packet['v6']['historical_session_2026-10-09']['report']['date_et'],'2026-10-09')
            packet={'v5':{},'samples_EXAMPLE':{'unsafe':'123456789:'+('x'*35)},'gaps':{}}
            with self.assertRaisesRegex(ValueError,'SECRET'):compact_historical_duplicates(packet,root,None,None)


if __name__=='__main__':unittest.main()
