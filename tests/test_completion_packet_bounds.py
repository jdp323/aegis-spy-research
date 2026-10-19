import hashlib,json,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from ops.completion_verification import latest_session,compact_historical_duplicates
from ops.verification_packet import write,scan

class CompletionPacketBounds(unittest.TestCase):
 def test_latest_completed_session_preserves_asof_and_rejects_future_or_holiday(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);folder=root/'daily_reports';folder.mkdir()
   original={'date_et':'2026-10-16','generated_at_utc':'2026-10-17T16:24:47+00:00','status':'PASS','LIVE_SIGNAL_READY':False,'minute_coverage':[{'hour_et':'09:00','expected':30,'recorded':30,'backfilled':12,'NO_PRINT_CONFIRMED':0,'missing':0}],'messages':{'trend_valid':6,'trend_stale':19,'receipt_statuses':{'TELEGRAM_ACCEPTED':25}},'clock_stream':{'events_by_type':{'CONNECT':3,'PROCESS_PAUSED':1}},'frames':{'by_hour':{'09:00 ET':{'1m':{'available':10}}}},'idea_engine':{'trace_count':3270},'outside_allowlist':'private-fixture-marker'}
   path=folder/'SESSION_REPORT_2026-10-16.json';path.write_text(json.dumps(original))
   for day in ('2026-10-17','2026-10-19'):(folder/f'SESSION_REPORT_{day}.json').write_text(json.dumps(dict(original,date_et=day)))
   before={p.name:p.read_bytes() for p in folder.iterdir()}
   result=latest_session(root,datetime(2026,10,17,17,tzinfo=timezone.utc))
   self.assertEqual(result['date_et'],'2026-10-16');self.assertEqual(result['saved_report_generated_at_utc'],original['generated_at_utc'])
   self.assertEqual(result['report']['messages']['trend_stale'],19);self.assertEqual(result['report']['minute_coverage'],original['minute_coverage'])
   self.assertNotIn('private-fixture-marker',json.dumps(result));self.assertFalse(result['report']['LIVE_SIGNAL_READY'])
   self.assertEqual(result['artifact']['sha256'],hashlib.sha256(path.read_bytes()).hexdigest())
   self.assertEqual(before,{p.name:p.read_bytes() for p in folder.iterdir()})
 def test_duplicate_evidence_compacts_with_hashes_and_old_session_explicitly_historical(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/'research').mkdir()
   command=root/'research/COMMAND_VERIFICATION_fixture.json';command.write_text('{"status":"PASS"}')
   schedule=root/'research/SCHEDULE_VERIFICATION_fixture.json';schedule.write_text('{"status":"PASS"}')
   (root/'TELEGRAM_MESSAGE_EXAMPLES.md').write_text('EXAMPLE: Watch only—option pricing unavailable.',encoding='utf-8')
   packet={'v5':{'commands':{'status':'PASS','command_count':36,'cases':180,'passed':180,'failed':0,'rows':[{'EXAMPLE_excerpt':'x'*400} for _ in range(120)]},'schedule_verification':{'status':'PASS','scenarios':[{'PASS':True,'full_text':'x'*1000} for _ in range(24)]}},'v6':{'last_session':{'date_et':'2026-10-09','status':'WARN'}},'samples_EXAMPLE':{'preopen_V5':'x'*8000,'no_trade_EXAMPLE':'EXAMPLE: wait'},'gaps':{'DECISIONS.md':{'excerpt':'x'*1500}}}
   before=len(json.dumps(packet,indent=2).encode());compact_historical_duplicates(packet,root,command,schedule)
   self.assertLess(len(json.dumps(packet,indent=2).encode()),before/4)
   self.assertEqual(packet['v5']['commands']['passed'],180);self.assertEqual(packet['v5']['schedule_verification']['scenario_count'],24)
   self.assertNotIn('last_session',packet['v6']);self.assertEqual(packet['v6']['historical_session_2026-10-09']['report']['date_et'],'2026-10-09')
   self.assertEqual(packet['v5']['commands']['evidence']['sha256'],hashlib.sha256(command.read_bytes()).hexdigest())
   self.assertFalse(scan(json.dumps(packet)));output=write(packet,root/'packet');self.assertLess(output.stat().st_size,150000)
   self.assertEqual(json.loads(output.with_suffix('.json').read_text())['v5']['commands']['passed'],180)
 def test_secret_in_removed_detail_still_refuses_and_packet_limit_stays_strict(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)
   unsafe={'v5':{'commands':{'rows':[{'text':'123456789:'+('x'*35)}]}},'samples_EXAMPLE':{},'gaps':{}}
   with self.assertRaisesRegex(ValueError,'SECRET'):compact_historical_duplicates(unsafe,root,None,None)
   with self.assertRaisesRegex(ValueError,'TOO_LARGE'):write({'unbounded':'x'*150001},root/'packet')
   self.assertFalse(list((root/'packet').iterdir()))
 def test_missing_session_is_unavailable_and_session_secret_is_not_hidden(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);self.assertEqual(latest_session(root,datetime(2026,10,17,tzinfo=timezone.utc))['status'],'UNAVAILABLE')
   (root/'daily_reports').mkdir();(root/'daily_reports/SESSION_REPORT_2026-10-16.json').write_text(json.dumps({'date_et':'2026-10-16','status':'PASS','outside_allowlist':'123456789:'+('x'*35)}))
   with self.assertRaisesRegex(ValueError,'SECRET'):latest_session(root,datetime(2026,10,17,tzinfo=timezone.utc))
