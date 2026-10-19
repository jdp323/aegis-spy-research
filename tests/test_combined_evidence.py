import unittest,tempfile,copy,sqlite3
from pathlib import Path
from datetime import timedelta
from unittest.mock import patch
from tests import test_paper_upgrade_c as fixtures
NOW=fixtures.NOW
from core.signals import build
from core.upgrade_service import read_config,validate_config
from options.chain_sanity import verify
from backtesting.paper_engine import PaperEngine
from backtesting.option_baseline import open_baseline
from backtesting.premium_accuracy import Accuracy
from ops.report import option_paper_report

class EvidenceTests(unittest.TestCase):
 def signal(self):
  args=fixtures.PaperEligibilityTests().inputs();c=read_config();c['require_chain_sanity']=False
  return build(*args,NOW,c).dict(),args,c
 def test_neighbors_and_missing_grid_fail_closed(self):
  s,args,c=self.signal();best=s['option_contract'];below=copy.deepcopy(best);above=copy.deepcopy(best)
  below.update(strike=599,bid=2.2,ask=2.3);above.update(strike=601,bid=1.8,ask=1.9)
  self.assertEqual(verify(best,[below,best,above],NOW),[])
  self.assertIn('CHAIN_NEIGHBORS_UNAVAILABLE',verify(best,[best],NOW))
  above.update(bid=4,ask=4.1);self.assertIn('CHAIN_NEIGHBOR_PRICE_INCONSISTENCY',verify(best,[below,best,above],NOW))
  args[2]['chain_sanity_reasons']=['CHAIN_NEIGHBORS_UNAVAILABLE'];c['require_chain_sanity']=True
  self.assertFalse(build(*args,NOW,c).paper_eligible)
  c['require_chain_sanity']='yes'
  with self.assertRaises(ValueError):validate_config(c)
 def test_random_direction_baseline_separate_and_real_only(self):
  s,args,c=self.signal()
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'p.sqlite';real=PaperEngine(path);real.open(s,s['option_contract']['quote'],now=NOW);real.store.close()
   class ChooseOriginal:
    def choice(self,values):return 1
   with patch('backtesting.option_baseline.random.Random',return_value=ChooseOriginal()):r=open_baseline(path,s,None,c,args[4],NOW)
   self.assertEqual(r['signal']['benchmark'],'MATCHED_CLOCK_RANDOM_DIRECTION_V1')
   original=PaperEngine(path);base=PaperEngine(path,kind='paper_baseline')
   self.assertEqual(len(original.positions()),1);self.assertEqual(len(base.positions()),1)
   original.store.close();base.store.close()
   self.assertEqual(option_paper_report(path)['open_trades'],1)
   self.assertEqual(option_paper_report(path)['matched_clock_random_direction_baseline']['open_trades'],1)
   with patch('backtesting.option_baseline.random.Random') as rand:
    rand.return_value.choice.return_value=-1;self.assertEqual(open_baseline(path,s,None,c,args[4],NOW),'OPPOSITE_REAL_QUOTE_UNAVAILABLE')
 def test_accuracy_append_only_dedupe_and_stale_rejection(self):
  s,args,c=self.signal();u=copy.deepcopy(args[3]);u['payload']['mid']=s['t1'];oq=s['option_contract']['quote']
  with tempfile.TemporaryDirectory() as d:
   a=Accuracy(Path(d)/'p.sqlite');p={'signal':s}
   self.assertEqual(a.observe(p,u,oq,NOW),1);self.assertEqual(a.observe(p,u,oq,NOW),0)
   self.assertEqual(a.report()['overall']['n'],1)
   with self.assertRaises(sqlite3.IntegrityError):a.db.execute('DELETE FROM premium_estimates')
   stale=copy.deepcopy(oq);stale['source_timestamp']=(NOW-timedelta(minutes=1)).isoformat()
   self.assertEqual(a.observe(p,u,stale,NOW),0);a.close()
 def test_fake_demo_transport_labels_every_message(self):
  from ops.demo import FakeTransport,wrap
  f=FakeTransport();self.assertEqual(f.send(wrap('example')),f.messages[0])
  with self.assertRaises(ValueError):f.send('not labelled')
 def test_measured_clock_offset_blocks_option_path(self):
  s,args,c=self.signal();c['clock_health']={'state':'MEASURED','offset_seconds':3}
  result=build(*args,NOW,c);self.assertFalse(result.paper_eligible);self.assertIn('CLOCK_OFFSET_BEYOND_TOLERANCE',result.paper_blockers)
 def test_stale_review_hides_option_dollar_targets(self):
  from monitoring.exit_text import format_review
  s,args,c=self.signal();q=copy.deepcopy(s['option_contract']['quote']);q['source_timestamp']=(NOW-timedelta(minutes=1)).isoformat()
  text=format_review(q['symbol'],'DATA_WARNING',{'t1':603,'t2':604,'option_t1':9.87,'option_t2':10.98},args[3],q,NOW)
  self.assertNotIn('9.87',text);self.assertNotIn('10.98',text);self.assertIn('option targets UNAVAILABLE',text)
 def test_demo_does_not_override_non_data_gates(self):
  from ops.demo import fixture
  for name in ('call','put','swing'):
   f=fixture(name);self.assertEqual(f['signal']['score'],100);self.assertEqual(len(set(f['signal']['multi_timeframe_alignment'].values())),1)
   self.assertFalse(f['real_evaluation']['paper_eligible']);self.assertTrue(f['signal']['demo_only_data_gate_substitution'])
