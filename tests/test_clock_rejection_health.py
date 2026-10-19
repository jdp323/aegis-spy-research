"""Future clock diagnostics never accept, retime or fabricate market inputs."""
import json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from core.storage import Store
from data.stream import Stream
from core.feed_health import clock_text,text_for
from research.live_trend import evaluate,text_for as trend_text

class ClockRejectionTests(unittest.TestCase):
 def setUp(self):
  folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
  self.store=Store(Path(folder.name)/'state.sqlite');self.addCleanup(self.store.close)
  self.now=datetime.now(timezone.utc);self.stream=Stream(self.store,feed='iex')
  fixed=patch('data.stream.iso',return_value=self.now.isoformat());fixed.start();self.addCleanup(fixed.stop)
  self.quote={'T':'q','S':'SPY','bp':600,'ap':600.02,'t':(self.now+timedelta(seconds=.9)).isoformat(),'extra':'private-provider-body'}
 def test_future_quote_remains_rejected_with_original_source_and_receipt(self):
  self.assertFalse(self.stream.ingest(self.quote))
  diagnostic=self.store.get('stream_clock:iex')
  self.assertEqual(diagnostic['state'],'FUTURE_TIMESTAMP_REJECTED');self.assertAlmostEqual(diagnostic['ahead_seconds'],.9)
  self.assertEqual(diagnostic['source_timestamp'],self.quote['t']);self.assertEqual(diagnostic['received_timestamp'],self.now.isoformat())
  self.assertIsNone(self.store.get('research_quote:SPY:iex'));self.assertIsNone(self.store.get('quote:SPY'))
  self.assertIsNone(self.store.get('last_market:iex'));self.assertEqual(self.stream.last_source,{})
  self.assertNotIn('private-provider-body',json.dumps(diagnostic));self.assertNotIn('private-provider-body',str(self.store.db.execute('SELECT payload FROM audit').fetchall()))
 def test_future_quote_preserves_previous_verified_quote_and_watermark(self):
  valid={**self.quote,'t':(self.now-timedelta(seconds=1)).isoformat()}
  self.assertTrue(self.stream.ingest(valid))
  original=self.store.get('research_quote:SPY:iex');watermark=dict(self.stream.last_source)
  watchdog=self.store.get('last_market:iex')
  self.assertFalse(self.stream.ingest(self.quote))
  self.assertEqual(self.store.get('research_quote:SPY:iex'),original)
  self.assertEqual(self.stream.last_source,watermark);self.assertEqual(self.store.get('last_market:iex'),watchdog)
  self.assertIsNone(self.store.get('quote:SPY'))
 def test_bar_and_trade_delivery_cannot_clear_quote_clock_failure(self):
  self.stream.ingest(self.quote)
  self.assertTrue(self.stream.ingest({'T':'b','S':'SPY','t':(self.now-timedelta(minutes=1)).isoformat(),'o':600,'h':601,'l':599,'c':600,'v':100}))
  self.assertTrue(self.stream.ingest({'T':'t','S':'SPY','t':self.now.isoformat(),'p':600,'s':1}))
  self.assertEqual(self.store.get('stream_clock:iex')['state'],'FUTURE_TIMESTAMP_REJECTED')
  self.assertIsNone(self.store.get('research_quote:SPY:iex'))
 def test_stale_quote_cannot_clear_condition_but_valid_quote_can(self):
  self.stream.ingest(self.quote)
  self.assertFalse(self.stream.ingest({**self.quote,'t':(self.now-timedelta(seconds=20)).isoformat()}))
  self.assertEqual(self.store.get('stream_clock:iex')['state'],'FUTURE_TIMESTAMP_REJECTED')
  self.assertTrue(self.stream.ingest({**self.quote,'t':(self.now-timedelta(seconds=1)).isoformat()}))
  state=self.store.get('stream_clock:iex');self.assertEqual(state['state'],'CLEARED_BY_VALID_QUOTE')
  self.assertIn('not proof',state['note']);self.assertEqual(self.store.get('research_quote:SPY:iex')['provider'],'alpaca-iex')
  self.assertIsNone(self.store.get('quote:SPY'))
 def test_diagnostics_are_throttled_without_accepting_later_future_frames(self):
  with patch('data.stream.time.monotonic',side_effect=(100,101,106)):
   self.assertFalse(self.stream.ingest(self.quote));self.assertFalse(self.stream.ingest(self.quote))
   self.assertEqual(self.store.get('stream_clock:iex')['rejected_payloads_since_process_start'],1)
   self.assertFalse(self.stream.ingest(self.quote))
  self.assertEqual(self.store.get('stream_clock:iex')['rejected_payloads_since_process_start'],3)
  self.assertEqual(self.store.db.execute("SELECT count(*) FROM audit WHERE kind='future_timestamp_rejection'").fetchone()[0],1)
 def test_trend_explains_current_clock_rejection_without_quote_or_ratio(self):
  moment=datetime(2026,10,8,15,tzinfo=timezone.utc)
  self.store.put('stream:iex',{'state':'CONNECTED','at':moment.isoformat()})
  self.store.put('stream_clock:iex',{'state':'FUTURE_TIMESTAMP_REJECTED','at':moment.isoformat()})
  result=evaluate(self.store,moment);self.assertEqual(result['status'],'UNAVAILABLE')
  self.assertIn('computer clock',result['iex_reason']);self.assertIn('Check Windows time synchronization',trend_text(result,moment))
  self.assertNotIn('mid',result);self.assertNotIn('counts',result)
  later=evaluate(self.store,moment+timedelta(seconds=121));self.assertNotIn('computer clock',later.get('iex_reason',''))
 def test_feed_clock_caution_uses_et_and_stale_diagnostic_is_not_current_fact(self):
  moment=datetime(2026,10,8,15,tzinfo=timezone.utc)
  snap={'clock_health':{'iex':{'state':'FUTURE_TIMESTAMP_REJECTED','at':moment.isoformat()}},'research_underlying':{'quality':'DATA_INVALID','source_timestamp':moment.isoformat()}}
  text=text_for(snap,moment);self.assertIn('Windows time synchronization',text);self.assertIn('11:00:00 ET',text)
  self.assertIn('historical',clock_text(snap,moment+timedelta(seconds=121)))
  self.assertIn('UNVERIFIED',clock_text(snap,moment+timedelta(seconds=121)))

if __name__=='__main__':unittest.main()
