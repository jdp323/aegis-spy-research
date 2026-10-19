import unittest,tempfile,json
from pathlib import Path
from ops.demo import fixture,response,run,PREFIX,SUFFIX
from core.storage import Store
from core.signals import quote_valid,finalize,Signal
from data.providers import ProviderRouter,UnconfiguredProvider
from data.session_recorder import Recorder
from data.models import stamp
class DemoTests(unittest.TestCase):
 def test_actual_pipeline_and_real_rejection(self):
  f=fixture();self.assertGreater(f['features']['5m']['bars'],50);self.assertFalse(f['real_evaluation']['paper_eligible']);self.assertFalse(quote_valid(f['provider'].get_underlying_quote().view(f['now']),f['now']))
  data,_=ProviderRouter(f['provider'],UnconfiguredProvider(),UnconfiguredProvider()).request('get_underlying_quote','SPY');self.assertNotEqual(data.get('entitlement'),'REALTIME')
 def test_arithmetic_labels_and_isolation(self):
  state={'nonce':'fixture','stage':0,'scenario':'call'}
  for a,v in [('bought',''),('quantity','1'),('premium','2.40'),('fees','.65'),('time','2026-10-08T10:22:00-04:00'),('confirm','yes')]:
   t=response(state,a,v);self.assertTrue(t.startswith(PREFIX));self.assertTrue(t.endswith(SUFFIX))
  self.assertEqual(state['cost'],'240.65');self.assertIn('68.70',response(state,'sold','3.10'))
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'runtime').mkdir();p=root/'runtime/paper.sqlite';s=Store(p)
   with self.assertRaises(ValueError):s.put('quote',{'feed_quality':'SIMULATED'})
   with self.assertRaises(ValueError):s.event('demo','paper',{'quote':{'feed_quality':'SIMULATED'}})
   self.assertEqual(s.db.execute('SELECT count(*) FROM events').fetchone()[0],0);s.close()
   run({'text':'start','tenant':'owner'},root);self.assertFalse((root/'runtime/history.sqlite').exists());self.assertFalse((root/'options').exists())
 def test_user_nonce_and_duplicate_isolation(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);out=run({'text':'start'},root);nonce=json.loads((root/'monitoring/demo_sessions/owner.json').read_text())['nonce']
   a=run({'text':'next','nonce':nonce,'callback_id':'fixture'},root)
   self.assertIn('already processed',run({'text':'next','nonce':nonce,'callback_id':'fixture'},root)['text'])
   self.assertIn('Use /demo start',run({'text':'next','tenant':'a'*24,'nonce':nonce,'callback_id':'other'},root)['text'])
 def test_all_scenarios_have_generated_ideas_or_blockers(self):
  for name in ('call','put','swing','no-trade'):
   state={'nonce':'fixture','scenario':name,'stage':0};texts=[response(state) for _ in range(5)];self.assertTrue(all(PREFIX in t and SUFFIX in t for t in texts))
   self.assertIn('NO TRADE' if name=='no-trade' else 'BUY '+('PUT' if name=='put' else 'CALL')+' idea','\n'.join(texts))
