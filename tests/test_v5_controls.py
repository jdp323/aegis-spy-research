import unittest,copy,tempfile,json,hashlib
from pathlib import Path
from datetime import timedelta
from unittest.mock import patch
from tests.test_v5_ideas import NOW,seed,oq
from ops.day_simulation import MemoryStore,config,inputs
from backtesting.idea_tracker import IdeaTracker
from core.idea_service import tick,context,candidates,permit
from strategies.idea_setups import pending_triggers
class V5Controls(unittest.TestCase):
 def test_real_score_report_rejects_injected_simulated_row(self):
  with tempfile.TemporaryDirectory() as d:
   t=IdeaTracker(Path(d)/'ideas.sqlite');i=seed()
   with t.db:t.db.execute('INSERT INTO idea_events VALUES(?,?,?,?,?)',('fixture',i['signal_id'],'fixture',json.dumps(i),NOW.isoformat()))
   with self.assertRaises(ValueError):t.summary(NOW)
   t.close()
  t=IdeaTracker(simulation=True)
  with self.assertRaises(ValueError):t.append(seed(),'fixture',NOW.replace(tzinfo=None))
 def test_enabled_unmet_pending_levels_and_utc_storage(self):
  c=config();c['setup_enabled']={k:False for k in c['setup_enabled']}
  self.assertEqual(pending_triggers({'1m':{'close':500,'vwap_approx':500},'opening_range':{'high':501,'low':499}},c),[])
  s=MemoryStore();inputs(s,NOW);ideas,_=candidates(context(s,NOW,True),{'quality':'DATA_OK','risk':'NORMAL'},config(),NOW,True)
  early=NOW-timedelta(minutes=30);inputs(s,early);ideas,_=candidates(context(s,early,True),{'quality':'DATA_OK','risk':'NORMAL'},config(),early,True)
  for i in ideas:
   for k in ('timestamp','signal_expiry','max_hold_until'):self.assertTrue(i[k].endswith('+00:00'))
 def test_negative_suppression_and_explicit_override(self):
  s=MemoryStore();t=IdeaTracker(simulation=True);i=seed();c=config()
  for n in range(50):t.append(dict(i,signal_id=str(n),status='CLOSED',r_multiple=-1,closed_at=NOW.isoformat()),'fixture',NOW)
  day=NOW.astimezone(__import__('core.sessions',fromlist=['ET']).ET).date().isoformat();s.put('idea-control:'+day,{'alerts':0,'last':{},'cooloff_until':None,'loss_checkpoint':'49'})
  self.assertEqual(permit(s,t,i,c,NOW)[0],'NEGATIVE_EVIDENCE')
  c['negative_setup_overrides']=['VWAP_RECLAIM'];self.assertIsNone(permit(s,t,i,c,NOW)[0])
 def test_new_ideas_not_old_eight_cap_owner_only_and_toggle(self):
  c=config();s=MemoryStore();t=IdeaTracker(simulation=True);early=NOW-timedelta(minutes=30);inputs(s,early);base=candidates(context(s,early,True),{'quality':'DATA_OK','risk':'NORMAL'},c,early,True)[0][0];messages=[]
  for n in range(9):
   now=early+timedelta(seconds=n);inputs(s,now);i=dict(base,signal_id=hashlib.sha256(str(n).encode()).hexdigest()[:24],trigger=base['trigger']+n,timestamp=now.isoformat())
   with patch('core.idea_service.candidates',return_value=([i],None)):tick(s,{'quality':'DATA_OK','risk':'NORMAL'},c,now,messages.append,tracker=t,simulation=True)
  self.assertEqual(sum(e['alert_type']=='SPY_IDEA' for e in messages),9);self.assertTrue(all(e['audience']=='PRIVATE' for e in messages));self.assertFalse(c.get('live_signal_enabled',False));self.assertFalse(c.get('order_execution_enabled',False))
  c['notifications']['categories']['ideas']=False;day=early.astimezone(__import__('core.sessions',fromlist=['ET']).ET).date().isoformat();before=s.get('idea-control:'+day)['alerts'];i=dict(base,signal_id='f'*24,trigger=600)
  now=early+timedelta(seconds=9);inputs(s,now)
  with patch('core.idea_service.candidates',return_value=([i],None)):tick(s,{'quality':'DATA_OK','risk':'NORMAL'},c,now,messages.append,tracker=t,simulation=True)
  self.assertEqual(before,s.get('idea-control:'+day)['alerts']);self.assertFalse(t.positions()[-1]['alerted'])
 def test_shared_only_explicit_and_preview_no_mutation(self):
  s=MemoryStore();t=IdeaTracker(simulation=True);i=seed();self.assertIsNone(permit(s,t,i,config(),NOW,preview=True)[0]);self.assertEqual(s.data,{})
  c=config();c['signals']['shared']=True;early=NOW-timedelta(minutes=31);inputs(s,early);out=[];tick(s,{'quality':'DATA_OK','risk':'NORMAL'},c,early,out.append,tracker=t,simulation=True);self.assertTrue(out);self.assertTrue(all(x['audience']=='SHARED' for x in out))
