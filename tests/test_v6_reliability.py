import unittest,tempfile,json,sqlite3,copy,asyncio
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from core.sessions import ET
from core.storage import Store
from core.isolation import assert_real
from data.models import quote
from data.reliability import Events,PauseProbe,watchdog_age,quote_diagnostics,describe,active
from data.backfill import Backfill,history,continuity
from data.providers import AlpacaProvider
from core.observed_context import evaluate
from ops.day_simulation import MemoryStore,config,inputs
NOW=datetime(2026,10,9,11,0,tzinfo=ET).astimezone(timezone.utc)
def bar(t,c=500,volume=100):return {'t':t.isoformat(),'o':c,'h':c+.1,'l':c-.1,'c':c,'v':volume}
def q(now=NOW,**updates):return {**quote('alpaca-iex','SPY',{'t':now.isoformat(),'bp':499.99,'ap':500.01},received=now.isoformat()).view(now),**updates}
class ReliabilityTests(unittest.TestCase):
 def test_event_allowlist_no_payload_or_secret(self):
  with tempfile.TemporaryDirectory() as d:
   e=Events(Path(d)/'e.sqlite')
   with self.assertRaises(ValueError):e.add('CONNECT','iex',NOW,token='forbidden')
   with self.assertRaises(ValueError):e.add('DISCONNECT','iex',NOW,reason='https://unsafe')
   e.add('CONNECT','iex',NOW);self.assertEqual(e.db.execute('SELECT count(*) FROM stream_events').fetchone()[0],1)
   with self.assertRaises(sqlite3.Error):e.db.execute('DELETE FROM stream_events')
   e.close()
 def test_pause_detected_with_wall_and_monotonic(self):
  p=PauseProbe();self.assertIsNone(p.check(NOW,10));r=p.check(NOW+timedelta(seconds=120),130);self.assertEqual(r['duration_seconds'],120);self.assertEqual(r['clock_jump_seconds'],0)
 def test_clock_jump_distinct_from_pause(self):
  p=PauseProbe();p.check(NOW,0);r=p.check(NOW+timedelta(seconds=120),1);self.assertEqual(r['clock_jump_seconds'],119)
 def test_backward_clock_jump_is_observed(self):
  p=PauseProbe();p.check(NOW,0);r=p.check(NOW-timedelta(seconds=120),1);self.assertEqual(r['clock_jump_seconds'],-121);self.assertEqual(r['reason'],'CLOCK_JUMP')
 def test_no_pause_from_short_interval_or_closed_session(self):
  p=PauseProbe();p.check(NOW,0);self.assertIsNone(p.check(NOW+timedelta(seconds=30),30));closed=NOW+timedelta(days=1);p=PauseProbe();p.check(closed,0);self.assertIsNone(p.check(closed+timedelta(seconds=120),120))
 def test_watchdog_ignores_control_heartbeat(self):
  self.assertEqual(watchdog_age({'received_timestamp':(NOW-timedelta(seconds=90)).isoformat()},NOW,NOW),90)
  self.assertEqual(watchdog_age({},NOW,NOW-timedelta(seconds=300)),300)
 def test_fake_socket_reconnects_without_market_frames(self):
  from data.stream import Stream
  class Clock:
   elapsed=0
   @classmethod
   def now(cls,tz):return NOW+timedelta(seconds=cls.elapsed)
  class Socket:
   sent=[];count=0
   async def recv(self):self.count+=1;Clock.elapsed+=31;return json.dumps([{'msg':'authenticated'}])
   async def send(self,v):self.sent.append(json.loads(v)['action'])
  class Connection:
   async def __aenter__(self):self.ws=Socket();return self.ws
   async def __aexit__(self,*a):return False
  store=MemoryStore();store.audit=lambda *a:None;store.put('last_market:iex',{'received_timestamp':(NOW-timedelta(seconds=91)).isoformat()});s=Stream(store,feed='iex',connect=lambda *a,**k:Connection());logs=[];s.log=lambda ev,**kw:logs.append(ev)
  async def stop(seconds):s.stop.set()
  s.wait=stop
  with patch('data.stream.datetime',Clock),patch.dict('os.environ',{'APCA_API_KEY_ID':'fixture','APCA_API_SECRET_KEY':'fixture'}):asyncio.run(s.run())
  self.assertIn('WATCHDOG_RECONNECT',logs);self.assertIn('RECONNECT',logs);self.assertEqual(Socket.sent,['auth','subscribe'])
 def test_old_connection_age_cannot_prevent_new_socket_market_receive(self):
   from data.reliability import connection_watchdog_age
   old={'received_timestamp':(NOW-timedelta(hours=1)).isoformat()}
   self.assertEqual(connection_watchdog_age(old,NOW,NOW),0)
   self.assertEqual(connection_watchdog_age(old,NOW+timedelta(seconds=90),NOW),90)
   fresh={'received_timestamp':(NOW+timedelta(seconds=30)).isoformat()}
   self.assertEqual(connection_watchdog_age(fresh,NOW+timedelta(seconds=60),NOW),30)
   future={'received_timestamp':(NOW+timedelta(seconds=120)).isoformat()}
   self.assertEqual(connection_watchdog_age(future,NOW+timedelta(seconds=60),NOW),60)
   self.assertEqual(watchdog_age(old,NOW,NOW),3600)
 def test_supervisor_restart_300_boundary(self):
  from ops.supervisor import stream_restart_due
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);s=Store(r/'runtime/aegis.sqlite');s.put('stream:iex',{'state':'CONNECTED'});s.put('last_market:iex',{'received_timestamp':(NOW-timedelta(seconds=300)).isoformat()});s.close()
   self.assertTrue(stream_restart_due(r,NOW,NOW-timedelta(seconds=300)));self.assertFalse(stream_restart_due(r,NOW,NOW-timedelta(seconds=299)))
 def test_signed_receipt_after_clock(self):
  d=quote_diagnostics(q(received_timestamp=(NOW+timedelta(seconds=.1)).isoformat()),NOW,'alpaca-iex');self.assertEqual(d['predicate'],'RECEIPT_AFTER_CLOCK');self.assertLess(d['receipt_age_seconds'],0);self.assertIn('-0.100',describe(d))
 def test_source_age_boundary_and_provider(self):
  self.assertIsNone(quote_diagnostics(q(NOW-timedelta(seconds=5)),NOW,'alpaca-iex')['predicate'])
  self.assertEqual(quote_diagnostics(q(NOW-timedelta(seconds=5.001)),NOW,'alpaca-iex')['predicate'],'SOURCE_TOO_OLD')
  self.assertEqual(quote_diagnostics(q(),NOW,'alpaca-sip')['predicate'],'PROVIDER_MISMATCH')
 def test_skew_and_invalid_bid_ask_predicates(self):
  self.assertEqual(quote_diagnostics(q(source_timestamp=(NOW+timedelta(seconds=.1)).isoformat()),NOW)['predicate'],'SOURCE_AFTER_CLOCK')
  self.assertEqual(quote_diagnostics(q(payload={'bid':501,'ask':500}),NOW)['predicate'],'QUALITY_ENTITLEMENT_OR_BID_ASK_INVALID')
 def test_rest_pagination_feed_tags(self):
  calls=[]
  def transport(path,p):
   calls.append(p.copy());return {'bars':[bar(NOW-timedelta(minutes=3 if len(calls)==1 else 2))],'next_page_token':'page' if len(calls)==1 else None}
  rows=history(AlpacaProvider(transport),NOW-timedelta(minutes=4),NOW,'iex');self.assertEqual(len(rows),2);self.assertTrue(all(r['feed_quality']=='IEX' and r['source']=='REST_BACKFILL' for r in rows));self.assertTrue(all(p['feed']=='iex' for p in calls))
 def test_backfill_idempotency_and_preservation(self):
  with tempfile.TemporaryDirectory() as d:
   b=Backfill(Path(d)/'b.sqlite',AlpacaProvider(lambda *a:{'bars':[bar(NOW-timedelta(minutes=4)),bar(NOW-timedelta(minutes=2))]}));s=MemoryStore()
   first=b.run(s,NOW);second=b.run(s,NOW);self.assertEqual(first['confirmed'],1);self.assertEqual(second['confirmed'],0);self.assertEqual(len(s.get('research_stream_bars:SPY:iex')),2);self.assertIsNone(s.get('stream_bars:SPY'));b.close()
 def test_authorization_failure_creates_no_confirmations(self):
  with tempfile.TemporaryDirectory() as d:
   def denied(*a):raise RuntimeError('HTTP_403')
   b=Backfill(Path(d)/'b.sqlite',AlpacaProvider(denied));s=MemoryStore();self.assertEqual(b.run(s,NOW)['status'],'UNAVAILABLE');self.assertEqual(b.db.execute('SELECT count(*) FROM bar_confirmations').fetchone()[0],0);self.assertIsNone(s.get('research_stream_bars:SPY:iex'));b.close()
 def test_incomplete_page_creates_no_confirmations(self):
  provider=AlpacaProvider(lambda *a:{'bars':[bar(NOW-timedelta(minutes=2))],'next_page_token':'same'})
  with self.assertRaises(ValueError):history(provider,NOW-timedelta(minutes=4),NOW)
 def test_feed_mismatch_and_simulated_rejected(self):
  for payload in ({'bars':[bar(NOW)],'feed':'sip'},{'bars':[dict(bar(NOW),feed_quality='SIMULATED')]}):
   with self.assertRaises(ValueError):history(AlpacaProvider(lambda *a:payload),NOW-timedelta(minutes=1),NOW,'iex')
 def test_empty_response_does_not_confirm_range(self):
  with tempfile.TemporaryDirectory() as d:
   b=Backfill(Path(d)/'b.sqlite',AlpacaProvider(lambda *a:{'bars':[]}));self.assertEqual(b.run(MemoryStore(),NOW)['status'],'UNAVAILABLE');self.assertEqual(b.db.execute('SELECT count(*) FROM bar_confirmations').fetchone()[0],0);b.close()
 def test_continuity_two_confirmed_empty_limit(self):
  real=[{'timestamp':i*60,'close':500,'volume':100} for i in range(31) if i not in (5,10)];slots,n=continuity(real,{300,600},0,1800);self.assertEqual((len(slots),n),(31,2));self.assertTrue(slots[5]['continuity_only'])
  with self.assertRaises(ValueError):assert_real(slots)
  with self.assertRaises(ValueError):continuity(real,{300},0,1800)
  with self.assertRaises(ValueError):continuity([b for b in real if b['timestamp']!=900],{300,600,900},0,1800)
 def test_real_store_rejects_continuity_slots(self):
  with tempfile.TemporaryDirectory() as d:
   s=Store(Path(d)/'s.sqlite')
   with self.assertRaises(ValueError):s.put('bad',{'continuity_only':True,'close':500})
   s.close()
 def test_context_heartbeat_and_bar_tail_reasons(self):
  s=MemoryStore();s.put('research_quote:SPY:iex',q());s.put('stream:iex',{'state':'CONNECTED','at':(NOW-timedelta(seconds=41)).isoformat()});self.assertEqual(evaluate(s,NOW)['failed_predicate'],'HEARTBEAT_AGE')
  s.put('stream:iex',{'state':'CONNECTED','at':NOW.isoformat()});self.assertEqual(evaluate(s,NOW)['failed_predicate'],'BAR_TAIL_UNAVAILABLE')
 def test_price_headline_not_false_frame_denominator(self):
  from core.idea_service import trend_line_details as trend_line
  s=MemoryStore();inputs(s,NOW);ctx=evaluate(s,NOW,True);ctx['direction']='UP';ctx['features'].update({k:{'trend':'UNAVAILABLE'} for k in ('5m','15m','30m','1h','daily')});ctx['features']['1m']['trend']='NEUTRAL';text=trend_line(ctx,NOW,config());self.assertIn('Price bias: UP',text);self.assertIn('0 of 1 available bullish (5 unavailable)',text);self.assertIn('do not confirm',text);self.assertNotIn('0 of 6',text)
 def test_trace_persists_blocked_before_return_and_aggregates(self):
  from core.rejection_trace import measure,persist
  with tempfile.TemporaryDirectory() as d:
   traces=measure({'reason':'missing quote'}, {},config(),NOW);p=Path(d)/'o.sqlite';persist(p,traces,NOW);persist(p,traces,NOW+timedelta(seconds=1));db=sqlite3.connect(p);rows=db.execute('SELECT payload,evaluation_count FROM rejection_traces').fetchall();self.assertTrue(rows);self.assertTrue(all(n==1 and json.loads(t)['blocker']=='missing quote' for t,n in rows));self.assertEqual(db.execute('SELECT COUNT(*) FROM rejection_trace_revisions').fetchone()[0],len(traces));db.close()
 def test_no_level_evaluations_go_to_reason_counters(self):
  from backtesting.forward_validation import ForwardValidation
  with tempfile.TemporaryDirectory() as d:
   f=ForwardValidation(Path(d)/'p.sqlite');s={'signal_id':'fixture','timestamp':NOW.isoformat(),'direction':'UNAVAILABLE','rejection_reasons':['DATA_MISSING']};self.assertIsNone(f.record(s));self.assertEqual(f.db.execute('SELECT count(*) FROM forward_evaluations').fetchone()[0],0);self.assertEqual(f.db.execute('SELECT evaluations FROM forward_reason_counts').fetchone()[0],1);f.close()
 def test_evidence_requires_fifty(self):
  from backtesting.idea_tracker import evidence
  self.assertEqual(evidence([{'status':'CLOSED','r_multiple':1}]*49)['evidence_tag'],'INSUFFICIENT DATA');self.assertEqual(evidence([{'status':'CLOSED','r_multiple':1}]*50)['evidence_tag'],'POSITIVE')
 def test_idea_gap_is_unresolved_then_recoverable_and_cost_applied(self):
  from tests.test_v5_ideas import seed,oq,NOW as t
  from backtesting.idea_tracker import IdeaTracker
  tracker=IdeaTracker(simulation=True);tracker.register(seed(),oq(),t);tracker.observe([dict(bar(t+timedelta(minutes=1)),l=498)],t+timedelta(minutes=2),feed_quality='SIMULATED');self.assertEqual(tracker.positions()[0]['coverage_status'],'UNRESOLVED_GAP');self.assertEqual(tracker.positions()[0]['status'],'OPEN')
  tracker.observe([dict(bar(t),l=498)],t+timedelta(minutes=2),feed_quality='SIMULATED');p=tracker.positions()[0];self.assertEqual(p['status'],'CLOSED');self.assertAlmostEqual(p['exit_price'],498.98);self.assertEqual(tracker.summary(t)['random_direction_baseline']['total'],1)
 def test_receipt_owner_confirmation_and_guest_refusal(self):
  from ops.receipts import listing,confirm
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);folder=r/'logs/notifications';folder.mkdir(parents=True);payload={'created_at':NOW.isoformat(),'kind':'RESEARCH','status':'PENDING_OR_UNCERTAIN'};(folder/'a.json').write_text(json.dumps(payload));guest=folder/'guests/fixture';guest.mkdir(parents=True);(guest/'b.json').write_text(json.dumps(payload));rows=listing(r);owner=next(x for x in rows if x['role']=='owner');g=next(x for x in rows if x['role']=='guest')
   with self.assertRaises(ValueError):confirm(g['receipt_hash'],r)
   confirm(owner['receipt_hash'],r);self.assertEqual(len(listing(r)),1)
   from ops.session_report import receipts
   self.assertEqual({x['role']:x['status'] for x in receipts(r,NOW.astimezone(ET).date().isoformat())},{'owner':'CONFIRMED_BY_OWNER','guest':'PENDING_OR_UNCERTAIN'})
 def test_sharing_count_no_identifiers(self):
  from monitoring.sharing import display
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);(r/'monitoring').mkdir();(r/'monitoring/access.json').write_text(json.dumps({'members':{'private-one':{'chat_id':'private'},'private-two':{'chat_id':'private'}}}));self.assertEqual(display({'signals':{'shared':True}},r),'signals.shared: ON (2 guests)');self.assertEqual(display({},r),'signals.shared: OFF')
 def test_session_report_closed_and_holiday(self):
  from ops.session_report import collect
  with tempfile.TemporaryDirectory() as d:
   self.assertEqual(collect('2026-10-10',Path(d))['status'],'NO_SESSION');self.assertEqual(collect('2026-11-26',Path(d))['status'],'NO_SESSION')
 def test_report_missing_capture_fails_without_fabrication(self):
  from ops.session_report import write
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);(r/'config').mkdir();(r/'config/upgrade.json').write_text(json.dumps({'live_signal_enabled':False,'order_execution_enabled':False}));p=write('2026-10-09',r,NOW.replace(hour=23));data=json.loads(p.with_suffix('.json').read_text());self.assertEqual(data['status'],'FAIL');self.assertEqual(sum(h['recorded'] for h in data['minute_coverage']),0);self.assertEqual(data['outages'][0]['logged_causes'],['UNKNOWN']);self.assertFalse(data['LIVE_SIGNAL_READY']);self.assertLess(p.stat().st_size,60000)
 def test_calendar_three_day_warning(self):
  from monitoring.simple_notifications import calendar_warning
  s=MemoryStore();sent=[];news={'verified_at':'2026-10-08T12:00:00+00:00','quality':'DATA_OK'};c={'notifications':{'categories':{'system':True}}}
  def send(*args,**kw):sent.append((args,kw))
  calendar_warning(s,news,datetime(2026,10,12,12,tzinfo=timezone.utc),send,c);calendar_warning(s,news,datetime(2026,10,12,12,tzinfo=timezone.utc),send,c);self.assertEqual(len(sent),1);self.assertIn('PRIVATE',sent[0][0])
 def test_live_and_sharing_flags_remain_exact(self):
  from core.upgrade_service import read_config
  from unittest.mock import patch
  import copy,json
  defaults=read_config();self.assertFalse(defaults['order_execution_enabled']);self.assertFalse(defaults['live_signal_enabled']);self.assertFalse(defaults['signals']['shared'])
  for shared in (False,True):
   with tempfile.TemporaryDirectory() as d:
    root=Path(d);(root/'config').mkdir();c=copy.deepcopy(defaults);c['signals']['shared']=shared
    (root/'config/upgrade.json').write_text(json.dumps(c))
    with patch('core.upgrade_service.ROOT',root):actual=read_config()
    self.assertFalse(actual['order_execution_enabled']);self.assertFalse(actual['live_signal_enabled'])
    if shared:self.assertTrue(actual['signals']['shared'])
    else:self.assertFalse(actual['signals']['shared'])
 def test_backfill_refreshes_native_frames_and_skips_closed_cadence(self):
  calls=[]
  def transport(path,p):
   calls.append(p['timeframe']);return {'bars':[bar(NOW-timedelta(minutes=3))]}
  with tempfile.TemporaryDirectory() as d:
   b=Backfill(Path(d)/'b.sqlite',AlpacaProvider(transport));s=MemoryStore();b.run(s,NOW)
   self.assertEqual(calls,['1Min','5Min','15Min','30Min','1Hour']);self.assertIn('1h',s.get('history_frames:iex'))
   closed=NOW+timedelta(days=1);b.warmed.add(('iex',closed.astimezone(ET).date().isoformat()));b.tick(s,closed);self.assertEqual(len(calls),5);b.close()
 def test_outage_warning_and_recovery_deduped_owner_only(self):
  from core.v6_service import Reliability
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);s=MemoryStore();clock=[NOW];sent=[];service=Reliability(s,AlpacaProvider(lambda *a:{}),r,clock=lambda:clock[0]);service.started=NOW-timedelta(minutes=2);service.backfill.tick=lambda *a:None
   def enqueue(*a,**kw):sent.append((a,kw))
   service.tick(clock[0],enqueue);service.tick(clock[0],enqueue);self.assertEqual(len(sent),1);self.assertEqual(sent[0][0][3],'PRIVATE');self.assertEqual(sent[0][1]['alert_type'],'DATA_WARNING')
   s.put('last_market:iex',{'received_timestamp':NOW.isoformat()});service.tick(clock[0],enqueue);service.tick(clock[0],enqueue);self.assertEqual(len(sent),2);self.assertEqual(sent[1][1]['alert_type'],'DATA_RECOVERY');service.events.close();service.backfill.close()
 def test_preopen_selfcheck_names_failed_heartbeat(self):
  from core.v6_service import Reliability
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);s=MemoryStore();now=NOW.astimezone(ET).replace(hour=9,minute=20).astimezone(timezone.utc);service=Reliability(s,AlpacaProvider(lambda *a:{}),r,clock=lambda:now);service.backfill.tick=lambda *a:None
   s.put('research_quote:SPY:iex',q(now));s.put('last_market:iex',{'received_timestamp':now.isoformat()});s.put('stream:iex',{'state':'CONNECTED','at':(now-timedelta(seconds=41)).isoformat()});out=[]
   service.tick(now,lambda *a,**kw:out.append(a));self.assertEqual(len(out),1);self.assertIn('Heartbeat age',out[0][2]);service.events.close();service.backfill.close()
 def test_opening_range_recovery_requires_all_genuine_minutes(self):
  from features.indicators import multi_timeframe
  opening=NOW.astimezone(ET).replace(hour=9,minute=30).astimezone(timezone.utc);rows=[bar(opening+timedelta(minutes=i)) for i in range(31)]
  self.assertIsNone(multi_timeframe(rows[1:],now=NOW)['opening_range']);self.assertIsNotNone(multi_timeframe(rows,now=NOW)['opening_range'])
 def test_native_history_warms_ema50_across_sessions_and_dst(self):
  from features.indicators import normalize,calculate
  rows=[]
  for month,day in ((10,30),(11,2),(11,3),(11,4)):
   opening=datetime(2026,month,day,9,30,tzinfo=ET).astimezone(timezone.utc)
   rows.extend(bar(opening+timedelta(minutes=i*15),500+len(rows)*.01+i*.01) for i in range(26))
  end=datetime(2026,11,5,10,tzinfo=ET).astimezone(timezone.utc);frames=normalize(rows,15,end);self.assertEqual(len(frames),104);self.assertIsNotNone(calculate(frames)['ema50']);self.assertNotEqual(stamp_for_test(rows[0]),stamp_for_test(rows[26]))
 def test_retention_views_preserve_archival_rows(self):
  with tempfile.TemporaryDirectory() as d:
   e=Events(Path(d)/'e.sqlite');e.add('CONNECT','iex',NOW-timedelta(days=400));self.assertEqual(e.db.execute('SELECT count(*) FROM stream_events').fetchone()[0],1);self.assertEqual(e.db.execute('SELECT count(*) FROM active_stream_events').fetchone()[0],0);e.close()
 def test_opening_backfill_at_0945_before_normal_cooldown(self):
  opening=NOW.astimezone(ET).replace(hour=9,minute=30).astimezone(timezone.utc);now=opening+timedelta(minutes=15);calls=[]
  def transport(path,p):
   calls.append(p);return {'bars':[bar(opening+timedelta(minutes=i)) for i in range(15)]}
  with tempfile.TemporaryDirectory() as d:
   b=Backfill(Path(d)/'b.sqlite',AlpacaProvider(transport));s=MemoryStore();b.warmed.add(('iex',now.astimezone(ET).date().isoformat()));b.next['iex']=now.timestamp()+200;b.tick(s,now)
   self.assertTrue(calls);self.assertEqual(calls[0]['end'],(opening+timedelta(minutes=14)).isoformat());self.assertEqual(len(s.get('research_stream_bars:SPY:iex')),15);b.close()
 def test_backfill_failure_reason_code_is_safe_and_exact(self):
  with tempfile.TemporaryDirectory() as d:
   b=Backfill(Path(d)/'b.sqlite',AlpacaProvider(lambda *a:{'bars':None}));self.assertEqual(b.run(MemoryStore(),NOW)['reason'],'MALFORMED_HISTORY_RESPONSE');b.close()
 def test_sip_entitlement_cooldown_does_not_starve_iex_history(self):
  import time
  provider=AlpacaProvider(lambda *a:{'bars':[bar(NOW-timedelta(minutes=2))]});provider.retry_at=time.monotonic()+300
  with tempfile.TemporaryDirectory() as d:
   b=Backfill(Path(d)/'b.sqlite',provider);self.assertEqual(b.run(MemoryStore(),NOW)['status'],'DATA_OK');self.assertGreater(provider.health()['retry_after_seconds'],0);b.close()
def stamp_for_test(row):return datetime.fromisoformat(row['t']).astimezone(ET).utcoffset()
if __name__=='__main__':unittest.main()
