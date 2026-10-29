"""Synthetic control clocks; real supervisor predicate and isolated SQLite."""
import json,sqlite3,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from ops.supervisor import stream_restart_due
from ops.day_simulation import MemoryStore
from data.stream import Stream
from data.models import quote
from data.reliability import quote_diagnostics

NOW=datetime(2026,10,29,17,tzinfo=timezone.utc)

class SupervisorControlProgressTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);(self.root/'runtime').mkdir()
  self.db=sqlite3.connect(self.root/'runtime/aegis.sqlite');self.db.execute('CREATE TABLE state(key TEXT PRIMARY KEY,payload TEXT NOT NULL)')
  self.started=NOW-timedelta(hours=1)
 def tearDown(self):self.db.close();self.temp.cleanup()
 def due(self,health,age=3600,started=None):
  with self.db:
   for key,value in [('stream:iex',health),('last_market:iex',{'received_timestamp':(NOW-timedelta(seconds=age)).isoformat()})]:self.db.execute('INSERT OR REPLACE INTO state VALUES(?,?)',(key,json.dumps(value)))
  return stream_restart_due(self.root,NOW,self.started if started is None else started)
 def health(self,state='FEED_DISCONNECTED',age=1,attempt_age=10,**extra):
  return {'state':state,'at':(NOW-timedelta(seconds=age)).isoformat(),'connection_started_at':(NOW-timedelta(seconds=attempt_age)).isoformat(),'error_type':'PermissionError','next_retry_seconds':300,**extra}
 def test_declared_permission_wait_is_not_a_hung_process(self):self.assertFalse(self.due(self.health()))
 def test_retry_handoff_has_bounded_five_second_grace(self):
  self.assertFalse(self.due(self.health(age=304.999,attempt_age=320)))
  self.assertTrue(self.due(self.health(age=305,attempt_age=320)))
 def test_real_jittered_permission_delay_is_honored(self):
  self.assertFalse(self.due(self.health(age=305.749,attempt_age=320,next_retry_seconds=300.75)))
  self.assertTrue(self.due(self.health(age=305.75,attempt_age=320,next_retry_seconds=300.75)))
 def test_expired_wait_does_not_hide_a_hung_process(self):self.assertTrue(self.due(self.health(age=400,attempt_age=420)))
 def test_invalid_or_unbounded_retry_delay_is_not_trusted(self):
  for delay in (None,True,-1,301.001,999,'300',float('nan'),float('inf')):
   with self.subTest(delay=str(delay)):self.assertTrue(self.due(self.health(next_retry_seconds=delay)))
 def test_unknown_error_cannot_claim_permission_cooldown(self):self.assertTrue(self.due(self.health(error_type='UnexpectedError')))
 def test_old_process_control_record_cannot_defer_restart(self):self.assertTrue(self.due(self.health(attempt_age=3601)))
 def test_future_control_clock_cannot_defer_restart(self):self.assertTrue(self.due(self.health(age=-.1)))
 def test_future_attempt_clock_cannot_defer_restart(self):self.assertTrue(self.due(self.health(attempt_age=-.1)))
 def test_control_before_attempt_start_is_invalid(self):self.assertTrue(self.due(self.health(age=11,attempt_age=10)))
 def test_malformed_or_naive_control_timestamps_are_not_trusted(self):
  for field in ('at','connection_started_at'):
   for value in ('bad','2026-10-29T17:00:00',None):
    with self.subTest(field=field,value=value):self.assertTrue(self.due(self.health(**{field:value})))
 def test_connect_attempt_gets_forty_seconds_not_forever(self):
  self.assertFalse(self.due(self.health('CONNECTING',attempt_age=39.999)))
  self.assertTrue(self.due(self.health('CONNECTING',attempt_age=40)))
 def test_new_authenticated_connection_can_receive_market_messages(self):self.assertFalse(self.due(self.health('CONNECTED',attempt_age=89.999)))
 def test_idle_heartbeats_cannot_extend_ninety_second_attempt_limit(self):self.assertTrue(self.due(self.health('CONNECTED_IDLE',attempt_age=90)))
 def test_unknown_state_is_not_control_progress(self):self.assertTrue(self.due(self.health('UNKNOWN_STATE')))
 def test_legacy_record_preserves_original_three_hundred_boundary(self):
  self.assertTrue(self.due({'state':'CONNECTED'},age=300,started=NOW-timedelta(seconds=300)))
  self.assertFalse(self.due({'state':'CONNECTED'},age=300,started=NOW-timedelta(seconds=299)))
 def test_real_market_receipt_still_prevents_hung_stream_restart(self):self.assertFalse(self.due(self.health(age=400,attempt_age=420),age=2))
 def test_control_progress_cannot_refresh_old_bid_ask(self):
  self.assertFalse(self.due(self.health()))
  old=(NOW-timedelta(seconds=6)).isoformat();q=quote('alpaca-iex','SPY',{'t':old,'bp':500,'ap':500.02},received=old).view(NOW)
  self.assertEqual(quote_diagnostics(q,NOW,'alpaca-iex')['predicate'],'SOURCE_TOO_OLD')
 def test_stream_status_persists_attempt_start_separately(self):
  store=MemoryStore();stream=Stream(store,feed='iex');stream.started=NOW
  stream.status('FEED_DISCONNECTED',next_retry_seconds=300,error_type='PermissionError')
  self.assertEqual(store.get('stream:iex').get('connection_started_at'),NOW.isoformat())
 def test_market_ingest_preserves_attempt_identity_not_source_time(self):
  store=MemoryStore();stream=Stream(store,feed='iex');stream.log=lambda *a,**k:None
  current=datetime.now(timezone.utc);stream.started=current-timedelta(seconds=2)
  with patch('core.directional_research.capture_future_quote'):
   self.assertTrue(stream.ingest({'T':'q','S':'SPY','t':current.isoformat(),'bp':500,'ap':500.02},received=current.isoformat()))
  health=store.get('stream:iex');self.assertEqual(health.get('connection_started_at'),stream.started.isoformat())
  self.assertEqual(store.get('research_quote:SPY:iex')['source_timestamp'],current.isoformat())

if __name__=='__main__':unittest.main()
