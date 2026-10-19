import unittest,tempfile,hashlib
from pathlib import Path
from ops.demo import fixture,chart,v5_scene,response,PREFIX,SUFFIX
class V5Demo(unittest.TestCase):
 def test_distinct_scenario_chart_hashes(self):
  with tempfile.TemporaryDirectory() as d:
   hashes=[]
   for name in ('call','put','swing','no-trade'):
    f=fixture('call' if name=='no-trade' else name);f['scenario']=name;p=Path(d)/(name+'.png');chart(f,p);hashes.append(hashlib.sha256(p.read_bytes()).hexdigest())
   self.assertEqual(len(set(hashes)),4)
 def test_v5_flow_labelled_and_no_trade_progresses(self):
  text='\n'.join(v5_scene('call',n) for n in range(10))
  for word in ('PRE-OPEN','EARLY READ','IDEA','ENTRY TRIGGERED','TARGET_1_HIT','STOP HIT','IDEA EXPIRED','RECAP','SCORE'):self.assertIn(word,text)
  s={'nonce':'fixture','scenario':'no-trade','stage':4};a=response(s);self.assertEqual(s['stage'],5);self.assertTrue(a.startswith(PREFIX));self.assertTrue(a.endswith(SUFFIX))
