import copy,json,tempfile,unittest,statistics,math
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from core.storage import Store
from core.signals import Signal,option_quote_valid
from core.upgrade_service import read_config,validate_config
from data.models import quote
from data.providers import AlpacaProvider
from data.session_recorder import Recorder
from news.calendar_updater import SOURCES,update,parse_official_ics
from backtesting.forward_validation import ForwardValidation
from backtesting.proxy_engine import ProxyEngine,MODE
from monitoring.paper_alerts import lifecycle
from core.paper_actions import execute
from ops.live_verify import public_crosscheck,sample
from core.sessions import ET
from core.sessions import market_session

NOW=datetime(2026,10,8,15,tzinfo=timezone.utc)

class QualityTests(unittest.TestCase):
 def signal(self):
  return Signal('a'*24,NOW.isoformat(),NOW.isoformat(),'alpaca-iex',paper_eligible=True,paper_mode=MODE,feed_quality='IEX',direction='CALL',spy_price=100,invalidation=99,t1=101.5,t2=102,signal_expiry=(NOW+timedelta(minutes=10)).isoformat())
 def q(self,provider='alpaca-iex',now=NOW):
  return quote(provider,'SPY',{'bp':99.99,'ap':100.01,'t':now.isoformat()},received=now.isoformat()).view(now)
 def bar(self,now=NOW):return {'t':now.isoformat(),'o':100,'c':100,'h':100.5,'l':99.5,'v':1000}
 def test_official_reader_bounded_calendar(self):
  fixtures=Path(__file__).parent/'fixtures/official_calendar'
  def transport(url):return (fixtures/({'fed':'fed.html','bls':'bls_official_reader.txt','bea':'bea.html'}[next(k for k,v in SOURCES.items() if v.format(year=2026)==url)])).read_bytes()
  with tempfile.TemporaryDirectory() as tmp:
   result=update(Path(tmp),NOW,transport);self.assertTrue(result['published']);self.assertEqual(datetime.fromisoformat(result['coverage_through']).astimezone(ET).isoformat(),'2026-12-04T23:59:59-05:00');self.assertTrue(any(e.get('time_source')=='DATE_ONLY' for e in result['events']))
 def test_optional_official_ics_timezone_and_rejection(self):
  url='https://www.dol.gov/calendar/events.ics'
  text='BEGIN:VCALENDAR\nBEGIN:VEVENT\nSUMMARY:Unemployment insurance weekly claims\nDTSTART;TZID=America/New_York:20261109T083000\nEND:VEVENT\nEND:VCALENDAR'
  events,_=parse_official_ics(text.encode(),url,NOW);self.assertEqual(events[0]['time_utc'],'2026-11-09T13:30:00+00:00');self.assertEqual(events[0]['risk'],'MODERATE')
  with self.assertRaises(ValueError):parse_official_ics(text.replace('20261109T083000','20261101T013000').encode(),url,NOW)
  with self.assertRaises(ValueError):parse_official_ics(text.encode(),'https://example.test/calendar.ics',NOW)
 def test_config_live_and_new_values_fail_closed(self):
  c=read_config();self.assertFalse(c['options_risk_live_confirmed'])
  for key,value in [('live_signal_enabled',True),('order_execution_enabled',True),('allow_unvalidated_paper_trading','yes'),('paper_daily_message_cap',0),('signal_expiry_seconds',0),('calendar_official_extra_sources',['https://evil.test/events.ics']),('calendar_event_overrides',{'x':{'blackout_before_minutes':1}})]:
   bad=copy.deepcopy(c);bad[key]=value
   with self.assertRaises(ValueError,msg=key):validate_config(bad)
 def test_rest_option_quote_has_opra_provenance(self):
  symbol='SPY261009C00100000';actual=datetime.now(timezone.utc);provider=AlpacaProvider(lambda *args:{'quotes':{symbol:{'bp':1.,'ap':1.1,'t':actual.isoformat()}}});q=provider.get_option_quote(symbol).view()
  self.assertEqual(q['provider'],'alpaca-opra');self.assertTrue(option_quote_valid(q,datetime.now(timezone.utc)))
 def test_forward_feed_and_partial_bar_separation(self):
  with tempfile.TemporaryDirectory() as tmp:
   f=ForwardValidation(Path(tmp)/'p.sqlite');f.record(self.signal());bar={**self.bar(), 'h':103,'l':98}
   self.assertEqual(f.observe([bar],NOW+timedelta(minutes=1),'SIP'),0);self.assertEqual(f.observe([bar],NOW+timedelta(minutes=1),'IEX'),1);self.assertIn('STOP_FIRST',f.db.execute('SELECT payload FROM forward_outcomes').fetchone()[0]);f.close()
 def test_invalidation_rejects_stale_and_wrong_feed(self):
  with tempfile.TemporaryDirectory() as tmp:
   s=Store(Path(tmp)/'s.sqlite');s.event('candidate','paper_candidate',self.signal().dict());calls=[]
   q=self.q('alpaca-sip');q['payload']['mid']=98
   lifecycle(s,q,read_config(),lambda *a,**k:calls.append(a),NOW);self.assertFalse(calls)
   q=self.q();q['payload']['mid']=98;s.put('research_quote:SPY:iex',q);lifecycle(s,q,read_config(),lambda *a,**k:calls.append(a),NOW);self.assertEqual(len(calls),1);self.assertEqual(s.get('paper_terminal:'+'a'*24)['reason'],'SIGNAL_INVALIDATED');s.close()
 def test_proxy_time_stop_and_feed_filter(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=ProxyEngine(Path(tmp)/'p.sqlite');p.open(self.signal(),self.q(),read_config(),NOW)
   end=NOW+timedelta(minutes=59)
   self.assertFalse(p.mark([self.bar(end)],{'risk':'NORMAL','quality':'DATA_OK'},end+timedelta(minutes=1),feed_quality='SIP'))
   rows=[self.bar(NOW+timedelta(minutes=i)) for i in range(60)];changes=p.mark(rows,{'risk':'NORMAL','quality':'DATA_OK'},end+timedelta(minutes=1),feed_quality='IEX');self.assertEqual(changes[-1]['exit_reason'],'TIME_STOP');p.close()
 def test_proxy_partial_entry_bar_skipped(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=ProxyEngine(Path(tmp)/'p.sqlite');now=NOW+timedelta(seconds=5);s=self.signal();s.timestamp=now.isoformat();p.open(s,self.q(now=now),read_config(),now)
   bar={**self.bar(),'h':103,'l':98};self.assertFalse(p.mark([bar],{'risk':'NORMAL','quality':'DATA_OK'},NOW+timedelta(minutes=1)));self.assertEqual(p.positions()[0]['mfe_usd_per_share'],0);p.close()
 def test_public_crosscheck_provenance_and_age(self):
  with tempfile.TemporaryDirectory() as tmp:
   s=Store(Path(tmp)/'s.sqlite');d={'timestamp':(NOW-timedelta(minutes=5)).isoformat(),'price':100,'source_url':'https://query1.finance.yahoo.com/v8/finance/chart/SPY','fetched_at':NOW.isoformat()};s.put('public_live_crosscheck',d);self.assertEqual(public_crosscheck(s,NOW)['quality'],'PUBLIC_DELAY_UNVERIFIED');s.put('public_live_crosscheck',{**d,'source_url':'https://example.test'});self.assertEqual(public_crosscheck(s,NOW)['quality'],'UNAVAILABLE');s.close()
 def test_verify_same_minute_does_not_refetch(self):
  with tempfile.TemporaryDirectory() as tmp:
   s=Store(Path(tmp)/'s.sqlite');root=Path(tmp);(root/'daily_reports').mkdir();calls=[]
   with patch('ops.live_verify.ROOT',root):
    sample(s,NOW,lambda *a:calls.append(a) or {'quality':'UNAVAILABLE'});sample(s,NOW+timedelta(seconds=10),lambda *a:calls.append(a) or {'quality':'UNAVAILABLE'})
   self.assertEqual(len(calls),1);s.close()
 def test_log_action_requires_real_quote_and_actual_fill(self):
  with tempfile.TemporaryDirectory() as tmp:
   s=Store(Path(tmp)/'s.sqlite');signal=self.signal().dict();symbol='SPY261009C00100000';q=quote('alpaca-opra',symbol,{'bp':1,'ap':1.1,'t':NOW.isoformat()},received=NOW.isoformat()).view(NOW);signal['option_contract']={'symbol':symbol,'quote':q};s.event('candidate','paper_candidate',signal);reply=execute({'signal_id':signal['signal_id'],'action':'log'},s,NOW);self.assertIn('ACTUAL_PREMIUM',reply['text']);self.assertEqual(s.get('paper_fill_prompt:owner')['signal_id'],signal['signal_id']);self.assertFalse(s.events('paper'));s.close()
 def test_chart_creates_actual_png_and_replay(self):
  with tempfile.TemporaryDirectory() as tmp:
   s=Store(Path(tmp)/'s.sqlite');signal=self.signal().dict();s.event('candidate','paper_candidate',signal);start=NOW-timedelta(minutes=40);s.put('research_stream_bars:SPY:iex',[self.bar(start+timedelta(minutes=i)) for i in range(40)])
   with patch('core.paper_chart.ROOT',Path(tmp)):
    reply=execute({'signal_id':signal['signal_id'],'action':'chart'},s,NOW);self.assertEqual(Path(reply['photo']).read_bytes()[:8],b'\x89PNG\r\n\x1a\n');self.assertIn('already',execute({'signal_id':signal['signal_id'],'action':'chart'},s,NOW)['text'])
   s.close()
 def test_iv_rank_needs_sixty_comparable_trading_days_per_feed(self):
  with tempfile.TemporaryDirectory() as tmp:
   r=Recorder(Path(tmp)/'h.sqlite');day=datetime(2026,1,2,17,tzinfo=timezone.utc);n=0
   while n<60:
    if market_session(day)['active']:
     symbol='SPY'+(day+timedelta(days=25)).strftime('%y%m%d')+'C00100000';raw={'latestQuote':{'t':day.isoformat()},'greeksTimestamp':day.isoformat(),'greeks':{'delta':.5},'impliedVolatility':.2+n*.001};datum={'provider':'fixture-indicative','feed_quality':'INDICATIVE','payload':{'contracts':{symbol:raw}}};self.assertEqual(r.chain(datum,100,day),1);n+=1
     if n==59:self.assertFalse(r.iv_history()['iv_rank_enabled'])
    day+=timedelta(days=1)
   result=r.iv_history();self.assertTrue(result['iv_rank_enabled']);self.assertEqual(result['series']['INDICATIVE']['comparable_days'],60);self.assertEqual(result['series']['INDICATIVE']['iv_rank'],100);self.assertFalse(result['series']['OPRA']['enabled']);self.assertFalse(result['series']['INDICATIVE']['live_readiness']);r.close()
 def test_guest_cannot_query_owner_paper_when_sharing_disabled(self):
  from core.bot_commands import execute as command
  with tempfile.TemporaryDirectory() as tmp:
   store=Store(Path(tmp)/'state.sqlite')
   with patch('core.bot_commands.Store',return_value=store),patch('core.upgrade_service.read_config',return_value={'signals':{'shared':False}}):
    response=command({'command':'paper','tenant':'b'*24});self.assertIn('owner-only',response);self.assertIn('sharing is disabled',response)
 def test_proxy_gap_preserves_unresolved_position_until_backfill(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=ProxyEngine(Path(tmp)/'p.sqlite');p.open(self.signal(),self.q(),read_config(),NOW);later=NOW+timedelta(minutes=5);bar={**self.bar(later),'h':103,'l':98}
   changes=p.mark([bar],{'risk':'NORMAL','quality':'DATA_OK'},later+timedelta(minutes=1));self.assertEqual(changes[-1]['update_reason'],'DATA_GAP_POSITION_UNRESOLVED');self.assertEqual(p.positions()[0]['status'],'OPEN');self.assertNotIn('pnl_usd',p.positions()[0]);self.assertEqual(p.positions()[0]['mfe_usd_per_share'],0)
   rows=[self.bar(NOW+timedelta(minutes=i)) for i in range(5)]+[bar];changes=p.mark(rows,{'risk':'NORMAL','quality':'DATA_OK'},later+timedelta(minutes=1));self.assertEqual(changes[-1]['exit_reason'],'STOP_INVALIDATION');self.assertFalse(changes[-1]['coverage_incomplete']);p.close()
 def test_small_sample_interval_uses_correct_degrees_of_freedom(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=ProxyEngine(Path(tmp)/'p.sqlite');values=list(range(-3,4));rows=[{'status':'CLOSED','pnl_usd_per_share':v} for v in values]
   with patch.object(p,'positions',return_value=rows):summary=p.summary()['proxy']
   margin=summary['mean_95pct_ci'][1]-summary['mean_usd_per_share'];self.assertGreaterEqual(margin,2.447*statistics.stdev(values)/math.sqrt(7));self.assertLess(margin,2.45*statistics.stdev(values)/math.sqrt(7));p.close()
 def test_live_verify_root_isolation_does_not_refresh_production_cache(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);store=Store(root/'s.sqlite')
   with patch('data.trend_spy.refresh',side_effect=AssertionError('must not touch production source')):
    observation=sample(store,NOW,root=root)
   self.assertEqual(observation['public_crosscheck']['quality'],'UNAVAILABLE');self.assertTrue((root/'daily_reports/LIVE_VERIFY_2026-10-08.md').exists());store.close()
