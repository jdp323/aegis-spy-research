import unittest,tempfile,copy,json,sqlite3,hashlib,threading
from unittest.mock import patch
from pathlib import Path
from datetime import datetime,timezone,timedelta
from ops.day_simulation import MemoryStore,config
from core.primary_plan import current,reserve,state
from core.storage import Store
from core.idea_service import tick
from backtesting.idea_tracker import IdeaTracker
from monitoring.owner_messages import status_text,idea_text,update_text,recap_text
from test_complete_telegram_messages import idea,context,NOW
from data.stream import Stream
from data.models import quote

class PrimaryPlanTests(unittest.TestCase):
 def plan(self,id='a'):
  return dict(idea(),signal_id=id*24,entry_mode='ENTER NOW',entry_condition='a completed 1-minute close above SPY $499.50',atr=.5,do_not_chase=500.25,early=False,explanation=[],feed_quality='SIMULATED')
 def test_two_detections_emit_one_and_keep_secondary_observation(self):
  s=MemoryStore();t=IdeaTracker(simulation=True);ctx=context();ctx.update(rows=[],early=False,horizons={});ctx['quote']['feed_quality']='SIMULATED';ctx['feed_quality']='SIMULATED';ctx['bar_research']['rows']=[]
  a,b=self.plan('a'),self.plan('b');messages=[]
  with patch('core.idea_service.context',return_value=ctx),patch('core.idea_service.candidates',return_value=([a,b],None)):
   tick(s,{'quality':'DATA_OK','risk':'NORMAL'},config(),NOW,messages.append,tracker=t,simulation=True)
   tick(s,{'quality':'DATA_OK','risk':'NORMAL'},config(),NOW,messages.append,tracker=t,simulation=True)
  self.assertEqual(sum(e['alert_type']=='SPY_IDEA' for e in messages),1)
  rows=t.positions();self.assertEqual(len(rows),2);self.assertEqual(rows[1]['alert_blocker'],'PRIMARY_PLAN_ACTIVE');self.assertFalse(rows[1]['alerted'])
  self.assertEqual(current(s,rows,NOW)['signal_id'],'a'*24);self.assertIsNone(rows[0]['actual_reported_fill'])
 def test_restart_adoption_terminal_release_and_outage_does_not_close(self):
  s=MemoryStore();a=dict(self.plan(),status='OPEN',alerted=True)
  self.assertEqual(current(s,[a],NOW),a);reserve(s,a,NOW)
  self.assertEqual(current(s,[a],NOW+timedelta(hours=2)),a)
  self.assertEqual(state(a,NOW+timedelta(hours=2)),'EXIT CONDITION REACHED')
  self.assertIsNone(current(s,[dict(a,status='CLOSED')],NOW))
 def test_status_retains_hold_after_entry_expiry_without_inferred_personal_fill(self):
  a=dict(self.plan(),status='OPEN');text=status_text(context(),NOW+timedelta(minutes=15),{'quality':'DATA_OK','risk':'NORMAL'},plan=a)
  self.assertIn('HOLD',text);self.assertIn('no new entry',text);self.assertLessEqual(len(text.splitlines()),5);self.assertNotIn('you bought',text.lower())
 def test_compact_messages_and_cohort_recap(self):
  a=self.plan();self.assertIn('ENTRY CONFIRMED',idea_text(a,{},{}));self.assertLessEqual(len(idea_text(a,{},{}).splitlines()),9)
  self.assertIn('EXIT CONDITION REACHED',update_text(a,'STOP_HIT'))
  a.update(alerted=True,status='CLOSED');b=dict(a,signal_id='b'*24,alerted=False)
  r=recap_text([a,b],NOW,'UNAVAILABLE');self.assertIn('Ideas alerted: 1',r);self.assertIn('Alerted research: 1 closed',r);self.assertIn('1 silent observations separate',r);self.assertEqual(len(r.splitlines()),6)
  expired=dict(a,status='EXPIRED_NO_ENTRY');gap=dict(a,status='OPEN',coverage_status='UNRESOLVED_GAP')
  r=recap_text([expired,gap],NOW,'UNAVAILABLE');self.assertIn('expired/cancelled: 1',r);self.assertIn('0 closed · 0 open · 1 unresolved',r)
 def test_atomic_schedule_reservation_two_connections(self):
  with tempfile.TemporaryDirectory() as d:
   a=Store(Path(d)/'state.sqlite');b=Store(Path(d)/'state.sqlite')
   try:self.assertTrue(a.reserve('slot',{'v':1}));self.assertFalse(b.reserve('slot',{'v':2}));self.assertEqual(a.get('slot'),{'v':1})
   finally:a.close();b.close()
 def test_latest_append_query_sees_external_append_without_rewriting_history(self):
  with tempfile.TemporaryDirectory() as d:
   t=IdeaTracker(Path(d)/'i.sqlite');a=dict(self.plan(),feed_quality='IEX',status='OPEN');t.append(a,'REGISTER',NOW)
   other=IdeaTracker(Path(d)/'i.sqlite');other.append(dict(a,status='CLOSED'),'OBSERVE',NOW+timedelta(minutes=1));other.close()
   self.assertEqual(t.positions()[0]['status'],'CLOSED');self.assertEqual(t.db.execute('select count(*) from idea_events').fetchone()[0],2);t.close()
 def test_transport_receipt_is_not_processing_time(self):
  s=MemoryStore();stream=Stream(s,feed='iex');received=datetime.now(timezone.utc)-timedelta(seconds=2)
  with patch('core.directional_research.capture_future_quote'):
   stream.ingest({'T':'q','S':'SPY','t':received.isoformat(),'bp':500.,'ap':500.01},received.isoformat())
  self.assertEqual(s.get('research_quote:SPY:iex')['received_timestamp'],received.isoformat());self.assertGreater(s.get('stream:iex')['local_queue_delay_ms'],1000)
 def test_feed_read_loops_have_independent_threads_and_connections(self):
  import asyncio
  from data.stream import main
  barrier=threading.Barrier(3);calls=[]
  def fake(feed,options,budget,shutdown):
   calls.append((feed,options,threading.get_ident()));barrier.wait(timeout=2)
  with patch('data.stream.run_feed',side_effect=fake),patch('data.stream.signal.signal'),patch('core.upgrade_service.read_config',return_value={}):asyncio.run(main())
  self.assertEqual(len({x[2] for x in calls}),3);self.assertEqual({(x[0],x[1]) for x in calls},{('sip',False),('sip',True),('iex',False)})
 def test_normalization_still_rejects_unknown_year_holiday_and_after_early_close(self):
  from features.indicators import normalize
  from core.sessions import ET
  times=[datetime(2030,1,2,10,tzinfo=ET),datetime(2026,11,26,10,tzinfo=ET),datetime(2026,11,27,13,tzinfo=ET)]
  for t in times:
   self.assertEqual(normalize([{'t':t.isoformat(),'o':1,'h':1,'l':1,'c':1,'v':1}],now=t+timedelta(days=1)),[])

if __name__=='__main__':unittest.main()
