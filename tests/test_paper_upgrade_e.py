import unittest,tempfile
from pathlib import Path
from datetime import datetime,timezone,timedelta
from core.storage import Store
from core.signals import Signal
from data.models import quote
from monitoring.paper_alerts import candidate_alert,lifecycle,signal_text
NOW=datetime(2026,10,8,15,tzinfo=timezone.utc)
class PaperAlertTests(unittest.TestCase):
 def signal(self,id='one'):return Signal(id,NOW.isoformat(),NOW.isoformat(),'alpaca-iex',paper_eligible=True,paper_mode='UNDERLYING_PROXY_ONLY',feed_quality='IEX',direction='CALL',score=100,invalidation=99,t1=101,t2=102,signal_expiry=(NOW+timedelta(minutes=10)).isoformat()).dict()
 def test_owner_label_cap_dedupe_expiry(self):
  with tempfile.TemporaryDirectory() as tmp:
   store=Store(Path(tmp)/'db.sqlite');calls=[];fake=lambda *a,**kw:calls.append((a,kw));c={'paper_daily_message_cap':2,'signals':{'shared':False}}
   self.assertTrue(candidate_alert(store,self.signal(),c,fake,NOW));self.assertFalse(candidate_alert(store,self.signal(),c,fake,NOW));self.assertTrue(candidate_alert(store,self.signal('two'),c,fake,NOW));self.assertFalse(candidate_alert(store,self.signal('three'),c,fake,NOW));self.assertFalse(candidate_alert(store,self.signal('expired'),c,fake,NOW+timedelta(minutes=11)))
   for args,kwargs in calls:self.assertEqual(args[3:5],('PRIVATE','owner'));self.assertEqual(kwargs['kind'],'RESEARCH');self.assertIn('(PAPER / UNVALIDATED)',args[2]);self.assertNotIn('BUY',args[2]);self.assertNotIn('SELL',args[2]);self.assertIn('Option contract: UNAVAILABLE',args[2])
   store.close()
 def test_invalidation_and_signal_expiry(self):
  with tempfile.TemporaryDirectory() as tmp:
   store=Store(Path(tmp)/'db.sqlite');calls=[];fake=lambda *a,**kw:calls.append((a,kw));c={'paper_daily_message_cap':8};candidate_alert(store,self.signal(),c,fake,NOW)
   q=quote('alpaca-iex','SPY',{'bp':97.99,'ap':98.01,'t':NOW.isoformat()},received=NOW.isoformat()).view(NOW)
   lifecycle(store,q,c,fake,NOW);self.assertIn('SIGNAL_INVALIDATED',calls[-1][0][2]);count=len(calls);lifecycle(store,None,c,fake,NOW+timedelta(minutes=11));self.assertEqual(len(calls),count)
   candidate_alert(store,self.signal('expire'),c,fake,NOW);lifecycle(store,None,c,fake,NOW+timedelta(minutes=11));self.assertIn('SIGNAL_EXPIRED',calls[-1][0][2]);store.close()
