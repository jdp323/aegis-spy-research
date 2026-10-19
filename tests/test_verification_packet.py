import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
from ops.verification_packet import scan,redact,safe_config,write,requirements,database,collect
from core.storage import Store
class PacketTests(unittest.TestCase):
 def test_secret_refusal_redaction_and_allowlist(self):
  secret='123456789:'+('x'*35);self.assertTrue(scan(secret));self.assertNotIn(secret,redact(secret))
  cfg=safe_config({'symbols':['SPY'],'order_execution_enabled':False,'refresh_token':'fixture-sensitive-value','chat_id':123,'username':'private'})
  self.assertEqual(set(cfg),{'symbols','order_execution_enabled','heartbeat_configured'})
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(ValueError,'REFUSED'):write({'unsafe':secret},d)
   self.assertFalse(list(Path(d).iterdir()))
 def test_tags_are_not_inflated_to_tested(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'research').mkdir();(root/'implemented.py').write_text('pass')
   (root/'research/combined_requirements.json').write_text(json.dumps([{'id':'fixture','files':['implemented.py']},{'id':'missing','files':['missing.py']}]))
   self.assertEqual([r['status'] for r in requirements(root)],['IMPLEMENTED','NOT DONE'])
 def test_sqlite_inspection_is_read_only_and_no_network(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'test.sqlite';s=Store(p);s.put('fixture',{'safe':True});s.close();before=p.read_bytes()
   with patch('urllib.request.urlopen',side_effect=AssertionError('network forbidden')):r=database(p)
   self.assertEqual(p.read_bytes(),before);self.assertEqual(r['simulated_rows_by_table']['state'],0)
 def test_json_twin_and_size_guard(self):
  with tempfile.TemporaryDirectory() as d:
   p=write({'safe':'test','config':{'LIVE_SIGNAL_READY':False}},d);self.assertEqual(json.loads(p.with_suffix('.json').read_text())['safe'],'test')
   with self.assertRaisesRegex(ValueError,'TOO_LARGE'):write({'big':'x'*160000},d)
 def test_whole_collection_offline_does_not_change_operational_files(self):
   import shutil
   from core.storage import ROOT
   with tempfile.TemporaryDirectory() as d:
    root=Path(d)
    for name in ('monitoring/command_registry.cjs','monitoring/notifier.cjs','config/upgrade.json'):
     target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
    (root/'runtime').mkdir();s=Store(root/'runtime/aegis.sqlite');s.put('worker_health',{'state':'fixture'});s.close()
    before={str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()}
    with patch('urllib.request.urlopen',side_effect=AssertionError('network forbidden')),patch('data.questrade.QuestradeProvider',side_effect=AssertionError('provider forbidden')):
     result=collect(root,run_tests=False,live=False)
    self.assertFalse(result['safety']['LIVE_SIGNAL_READY'])
    for path,content in before.items():self.assertEqual(Path(path).read_bytes(),content)
    self.assertFalse((root/'runtime/paper.sqlite').exists())
 def test_v5_runtime_fields_are_allowlisted(self):
    from ops.v5_verification import extend
    with tempfile.TemporaryDirectory() as d:
     root=Path(d);(root/'research').mkdir()
     (root/'research/v5_backup.json').write_text(json.dumps({'ledgers_before':{}}))
     (root/'research/V5_RUNTIME_CHECK.json').write_text(json.dumps({'at':'2026-10-09T04:00:00+00:00','dashboard_http':200,'unknown_private_field':'must-never-appear','health':{'clock':{'at':'2026-10-09T04:00:00+00:00','state':'UNAVAILABLE','unknown_private_field':'must-never-appear'}}}))
     packet={'header':{},'deployment_observations':{},'safety':{},'samples_EXAMPLE':{},'migration_notes':{},'weak_points':[]}
     from datetime import datetime,timezone
     with patch('ops.demo.v5_scene',return_value='EXAMPLE'):
      extend(packet,root,datetime(2026,10,9,tzinfo=timezone.utc))
     self.assertNotIn('must-never-appear',json.dumps(packet))
     self.assertEqual(packet['v5']['runtime_check']['dashboard_http'],200)
     self.assertEqual(packet['v5']['runtime_check']['health']['clock']['state'],'UNAVAILABLE')
 def test_v5_packet_reports_current_opted_in_sharing_without_live_promotion(self):
     from ops.v5_verification import extend
     from datetime import datetime,timezone
     with tempfile.TemporaryDirectory() as d:
      root=Path(d);(root/'config').mkdir();(root/'research').mkdir()
      (root/'research/v5_backup.json').write_text(json.dumps({'ledgers_before':{}}))
      (root/'config/upgrade.json').write_text(json.dumps({'signals':{'shared':True}}))
      packet={'header':{},'deployment_observations':{},'safety':{'LIVE_SIGNAL_READY':False},'samples_EXAMPLE':{},'migration_notes':{},'weak_points':[]}
      with patch('ops.demo.v5_scene',return_value='EXAMPLE'),patch('urllib.request.urlopen',side_effect=AssertionError('network forbidden')):
       extend(packet,root,datetime(2026,10,9,tzinfo=timezone.utc))
      self.assertIn('signals.shared=true',packet['safety']['guest_routing'])
      self.assertIn('personal/admin replies private',packet['safety']['guest_routing'])
      self.assertIn('Uncertain delivery never replayed',packet['safety']['guest_routing'])
      self.assertFalse(packet['safety']['LIVE_SIGNAL_READY'])
 def test_v5_packet_missing_or_disabled_sharing_stays_owner_only(self):
     from ops.v5_verification import extend
     from datetime import datetime,timezone
     with tempfile.TemporaryDirectory() as d:
      root=Path(d);(root/'config').mkdir();(root/'research').mkdir()
      (root/'research/v5_backup.json').write_text(json.dumps({'ledgers_before':{}}))
      for config in ({},{'signals':{'shared':False}},{'signals':{'shared':'true'}}):
       with self.subTest(config=config):
        (root/'config/upgrade.json').write_text(json.dumps(config))
        packet={'header':{},'deployment_observations':{},'safety':{'LIVE_SIGNAL_READY':False},'samples_EXAMPLE':{},'migration_notes':{},'weak_points':[]}
        with patch('ops.demo.v5_scene',return_value='EXAMPLE'):extend(packet,root,datetime(2026,10,9,tzinfo=timezone.utc))
        self.assertIn('owner-only; signals.shared=false',packet['safety']['guest_routing'])
        self.assertFalse(packet['safety']['LIVE_SIGNAL_READY'])
