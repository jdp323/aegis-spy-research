import unittest,tempfile,json,hashlib,copy
from pathlib import Path
from datetime import datetime,timezone,timedelta
from core.sessions import ET
from core.idea_config import settings
from strategies.idea_setups import detect,pending_triggers,levels
from backtesting.idea_tracker import IdeaTracker,evidence
from core.idea_service import context,candidates,permit,tick,trend_line
from ops.day_simulation import MemoryStore,config,inputs,run_scenario
from data.models import quote
NOW=datetime(2026,10,9,10,16,tzinfo=ET).astimezone(timezone.utc)
def seed(direction='CALL',mode='ENTER NOW',quality='SIMULATED'):
 sign=1 if direction=='CALL' else -1
 return {'signal_id':'a'*24,'timestamp':NOW.isoformat(),'direction':direction,'setup_type':'VWAP_RECLAIM','early':False,'entry_mode':mode,'entry':500.,'spy_price':500.,'trigger':500.,'invalidation':500-sign,'t1':500+sign,'t2':500+2*sign,'signal_expiry':(NOW+timedelta(minutes=10)).isoformat(),'max_hold_until':(NOW+timedelta(minutes=60)).isoformat(),'feed_quality':quality,'atr':1.,'strategy_version':'spy-ideas-v1'}
def oq(now=NOW):return {'feed_quality':'SIMULATED','payload':{'bid':499.99,'ask':500.01,'mid':500},'source_timestamp':now.isoformat()}
class V5Ideas(unittest.TestCase):
 def test_each_enabled_setup_and_volume_higher_frame_rejection(self):
  for name,direction in [('OPENING_RANGE_BREAKOUT','CALL'),('OPENING_RANGE_BREAKDOWN','PUT'),('VWAP_RECLAIM','CALL'),('VWAP_REJECTION','PUT'),('TREND_CONTINUATION','CALL'),('SUPPORT_BOUNCE','CALL'),('RESISTANCE_REJECTION','PUT'),('BREAKOUT_RETEST','CALL')]:
   sign=1 if direction=='CALL' else -1;bars=[{'timestamp':NOW.timestamp()-60*(31-n),'open':500.,'high':501.,'low':499.,'close':500.,'volume':1000} for n in range(31)]
   bars[-2].update(close=500-sign*.1);bars[-1].update(close=500+sign*.1,high=500.2,low=499.8,volume=2500)
   f={'close':500+sign*.1,'atr14':.2,'vwap_approx':500.,'previous_vwap_approx':500.,'ema9':500.,'support':500.,'resistance':500.,'swing_highs':[],'swing_lows':[]}
   fs={'1m':f,'opening_range':{'high':500.,'low':500.},'15m':{'trend':'BULL' if sign==1 else 'BEAR'},'1h':{'trend':'BULL' if sign==1 else 'BEAR'}}
   if name=='BREAKOUT_RETEST':bars[-2]['close']=500.05
   q={'payload':{'mid':500+sign*.11},'feed_quality':'SIMULATED'}
   candidates_=detect(fs,bars,q,NOW,config())
   self.assertIn(name,[x['setup_type'] for x in candidates_],name)
   bars[-1]['volume']=1;self.assertFalse(detect(fs,bars,q,NOW,config()))
   bars[-1]['volume']=2500;fs['15m']['trend']=fs['1h']['trend']='BEAR' if sign==1 else 'BULL';self.assertFalse(detect(fs,bars,q,NOW,config()))
 def test_pending_levels_min_rr_and_atr_floor(self):
  triggers=pending_triggers({'1m':{'close':500,'vwap_approx':500,'support':499,'resistance':501},'opening_range':{'high':502,'low':498}})
  self.assertEqual({t['direction'] for t in triggers},{'CALL','PUT'})
  lv=levels(500,499.99,1,2,{},config());self.assertEqual(lv['invalidation'],499);self.assertGreaterEqual(lv['risk_reward'],2)
  self.assertIsNone(levels(500,499,1,1,{},dict(config(),min_rr=3)))
 def test_early_only_opening_range_and_fresh_tail(self):
  s=MemoryStore();early=NOW.astimezone(ET).replace(hour=9,minute=46).astimezone(timezone.utc);inputs(s,early)
  ctx=context(s,early,True);self.assertTrue(ctx['early']);ideas,why=candidates(ctx,{'quality':'DATA_OK','risk':'NORMAL'},config(),early,True)
  self.assertTrue(ideas,why);self.assertTrue(all(x['early'] and x['setup_type'].startswith('OPENING_RANGE') for x in ideas))
  self.assertFalse(candidates(ctx,{'quality':'DATA_OK','risk':'HIGH'},config(),early,True)[0])
  self.assertFalse(context(s,early+timedelta(seconds=6),True)['quote'])
 def test_long_short_stop_first_mfe_mae_and_separation(self):
  for direction in ('CALL','PUT'):
   t=IdeaTracker(simulation=True);i=seed(direction);t.register(i,oq(),NOW,True)
   b={'t':NOW.isoformat(),'o':500,'h':503,'l':497,'c':500,'feed_quality':'SIMULATED'}
   changes=t.observe([b],NOW+timedelta(minutes=2),feed_quality='SIMULATED');p=t.positions()[0]
   self.assertEqual(p['exit_reason'],'STOP_HIT');self.assertGreater(p['mfe'],2);self.assertGreater(p['mae'],2);self.assertEqual(len(changes),1)
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'ideas.sqlite';t=IdeaTracker(p)
   with self.assertRaises(ValueError):t.register(seed(),oq(),NOW)
   tables=[r[0] for r in t.db.execute("SELECT name FROM sqlite_master WHERE type='table'")];self.assertEqual(tables,['idea_events']);t.close()
 def test_expired_no_entry_forced_flat_and_same_feed(self):
  t=IdeaTracker(simulation=True);t.register(seed(mode='TRIGGER'),oq(),NOW)
  t.observe([],NOW+timedelta(minutes=11));self.assertEqual(t.positions()[0]['status'],'EXPIRED_NO_ENTRY');self.assertEqual(t.summary(NOW)['all']['closed'],0)
  t=IdeaTracker(simulation=True);i=seed();late=NOW.astimezone(ET).replace(hour=15,minute=53).astimezone(timezone.utc);i.update(timestamp=late.isoformat(),signal_expiry=(late+timedelta(minutes=1)).isoformat(),max_hold_until=(late+timedelta(hours=1)).isoformat());t.register(i,oq(late),late)
  b={'t':late.isoformat(),'o':500,'h':500.1,'l':499.9,'c':500,'feed_quality':'SIMULATED'}
  t.observe([b],late+timedelta(minutes=2),feed_quality='IEX');self.assertEqual(t.positions()[0]['status'],'OPEN')
  t.observe([b,dict(b,t=(late+timedelta(minutes=1)).isoformat())],late+timedelta(minutes=2),feed_quality='SIMULATED');self.assertEqual(t.positions()[0]['exit_reason'],'TIME_EXIT')
 def test_evidence_tags_negative_override_cooldown_cooloff_runaway(self):
  for value,tag in [(1,'POSITIVE'),(-1,'NEGATIVE'),(0,'UNCLEAR')]:
   rows=[dict(seed(),status='CLOSED',r_multiple=value) for _ in range(50)];self.assertEqual(evidence(rows)['evidence_tag'],tag)
  self.assertEqual(evidence([])['evidence_tag'],'INSUFFICIENT DATA')
  s=MemoryStore();t=IdeaTracker(simulation=True);i=seed();c=config()
  self.assertIsNone(permit(s,t,i,c,NOW)[0]);self.assertEqual(permit(s,t,i,c,NOW)[0],'DIRECTION_COOLDOWN')
  i=dict(i,trigger=502);self.assertIsNone(permit(s,t,i,c,NOW)[0])
  state=s.get('idea-control:'+NOW.astimezone(ET).date().isoformat());state['alerts']=40;s.put('idea-control:'+NOW.astimezone(ET).date().isoformat(),state)
  self.assertEqual(permit(s,t,dict(i,trigger=505),c,NOW)[0],'RUNAWAY_BREAKER')
  s=MemoryStore()
  for n in range(3):t.append(dict(seed(),signal_id=str(n),status='CLOSED',r_multiple=-1,closed_at=NOW.isoformat()),'fixture',NOW)
  blocked,_,warnings=permit(s,t,i,c,NOW);self.assertEqual(blocked,'COOL_OFF');self.assertTrue(any('COOL-OFF' in x for x in warnings))
 def test_config_validation_and_live_flags_never_changed(self):
  for bad in ({'trend_lines_silent':1},{'idea_daily_cap':0},{'min_rr':1},{'rough_risk_delta_range':[.6,.4]},{'setup_enabled':{'FAKE':True}}):
   with self.assertRaises(ValueError):settings(bad)
  from core.upgrade_service import read_config
  c=read_config();self.assertFalse(c['live_signal_enabled']);self.assertFalse(c['order_execution_enabled']);self.assertFalse(c['horizons']['swing_enabled'])
 def test_slot_counts_restart_weekend_holiday_early_close_dst(self):
  for name,day,start,restart in [('normal','2026-10-09',555,False),('late_restart','2026-10-09',667,True),('weekend','2026-10-10',555,False),('holiday','2026-11-26',555,False),('early_close','2026-11-27',555,False),('dst','2026-11-02',555,False)]:
   r=run_scenario(name,datetime.fromisoformat(day).date(),start,restart);self.assertTrue(r['PASS'])
   if name=='early_close':self.assertIn('13:15:00-05:00',[e['at_et'][-14:] for e in r['timeline'] if e['alert_type']=='RECAP'])
 def test_stale_once_recovery_and_simulated_rejected(self):
  r=run_scenario('stale',datetime(2026,10,9).date());stale=[e for e in r['timeline'] if e['alert_type']=='TREND_LINE' and 'New entry: WAIT' in e['text'] and 'SOURCE_TOO_OLD' in e['text']];self.assertEqual(len(stale),4)
  s=MemoryStore();inputs(s,NOW);self.assertIsNotNone(context(s,NOW)['reason'])
