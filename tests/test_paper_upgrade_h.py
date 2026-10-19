import unittest,tempfile,json
from pathlib import Path
from datetime import datetime,timezone,timedelta
from options.ledger import Ledger
from core.storage import Store
from core.signals import Signal
from core.paper_actions import execute
from ops.heartbeat import tick,validate_url
NOW=datetime(2026,10,8,15,tzinfo=timezone.utc)
class HardeningTests(unittest.TestCase):
 def test_duplicate_force_void_and_negative_guard(self):
  with tempfile.TemporaryDirectory() as tmp:
   ledger=Ledger(Path(tmp)/'reported.sqlite');symbol='SPY261009C00600000';time='2026-10-01T14:00:00+00:00'
   ledger.record('one','BUY',symbol,1,'2','0.65',time)
   with self.assertRaisesRegex(ValueError,'duplicate'):ledger.record('two','BUY',symbol,1,'2.0','0.650','2026-10-01T10:00:00-04:00')
   ledger.record('two','BUY',symbol,1,'2','0.65',time,force=True);self.assertEqual(ledger.positions()[0]['quantity'],2);ledger.record('sold','SELL',symbol,2,'3','0.65','2026-10-01T15:00:00+00:00')
   with self.assertRaisesRegex(ValueError,'negative'):ledger.void('bad-void','one')
   ledger.void('void-sale','sold');self.assertEqual(ledger.positions()[0]['quantity'],2);ledger.void('void-one','one');self.assertEqual(ledger.positions()[0]['quantity'],1);self.assertEqual(ledger.db.execute('SELECT count(*) FROM option_events').fetchone()[0],5);ledger.close()
 def test_owner_callback_expiry_and_replay(self):
  with tempfile.TemporaryDirectory() as tmp:
   s=Store(Path(tmp)/'s.sqlite');signal=Signal('a'*24,NOW.isoformat(),None,'fixture',signal_expiry=(NOW+timedelta(minutes=10)).isoformat()).dict();s.event('candidate','paper_candidate',signal);data={'signal_id':'a'*24,'action':'skip'}
   self.assertIn('skipped',execute(data,s,NOW)['text']);self.assertIn('already',execute(data,s,NOW)['text'])
   with self.assertRaises(ValueError):execute({**data,'tenant':'guest'},s,NOW)
   with self.assertRaises(ValueError):execute(data,s,NOW+timedelta(minutes=11))
   s.close()
 def test_optional_heartbeat_no_secrets_and_cadence(self):
  with tempfile.TemporaryDirectory() as tmp:
   s=Store(Path(tmp)/'s.sqlite');calls=[];transport=lambda url:calls.append(url)
   self.assertEqual(tick(s,{'heartbeat_url':''},{'active':True},NOW,transport)['state'],'DISABLED');self.assertFalse(calls)
   c={'heartbeat_url':'https://example.test/private-secret-path'};tick(s,c,{'active':True},NOW,transport);tick(s,c,{'active':True},NOW+timedelta(seconds=299),transport);tick(s,c,{'active':True},NOW+timedelta(seconds=300),transport);self.assertEqual(len(calls),2);self.assertNotIn('private-secret',json.dumps(s.get('external_heartbeat')))
   with self.assertRaises(ValueError):validate_url('http://example.test')
   s.close()
