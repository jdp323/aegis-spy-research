import unittest
from datetime import datetime,timedelta,timezone
from core.sessions import ET,market_session
from strategies.concretum import bands,decision,complete,share_count,session_replay

def day(t,change=0):
 s=market_session(t.replace(hour=10));start=t.replace(hour=9,minute=30,second=0,microsecond=0)
 return [dict(timestamp=(start+timedelta(minutes=n)).timestamp(),open=100,high=102+change,low=99,close=100+change,volume=100) for n in range(s['close_minute']-570)]

class OriginalRules(unittest.TestCase):
 def setUp(self):
  t=datetime(2026,9,1,tzinfo=ET);self.days=[]
  while len(self.days)<16:
   if market_session(t.replace(hour=10))['active']:self.days.append(day(t,1))
   t+=timedelta(days=1)
 def test_exact_fourteen_prior_slots_and_missing_dividend_refusal(self):
  today=self.days[-1][:30];b=bands(today,self.days[:14],101,0)
  self.assertAlmostEqual(b['sigma'],.01);self.assertAlmostEqual(b['upper'],102.01)
  self.assertEqual(bands(today,self.days[:13],101,0)['status'],'UNAVAILABLE');self.assertEqual(bands(today,self.days[:14],101,None)['status'],'UNAVAILABLE')
 def test_decisions_are_completed_half_hours_not_current_unfinished_candle(self):
  self.assertEqual(decision(self.days[-1][:29],self.days[:14],101,0)['status'],'ABSTAIN')
  r=decision(self.days[-1][:30],self.days[:14],101,0);self.assertEqual(datetime.fromisoformat(r['decision_at']).astimezone(ET).strftime('%H:%M'),'10:00')
 def test_opposite_band_holds_inside_noise_refined_closes(self):
  today=day(datetime(2026,10,1,tzinfo=ET))[:30]
  self.assertEqual(decision(today,self.days[:14],100,0,1,'OPPOSITE_BAND')['side'],1)
  self.assertEqual(decision(today,self.days[:14],100,0,1,'CURRENT_BAND_VWAP')['side'],0)
 def test_early_close_and_unknown_year_fail_closed(self):
  self.assertTrue(complete(day(datetime(2026,11,27,tzinfo=ET))));self.assertFalse(complete(self.days[-1][1:]));self.assertIsNone(share_count(100000,100,[],True))
 def test_delayed_adaptation_never_uses_decision_bar_for_entry(self):
  today=day(datetime(2026,10,1,tzinfo=ET),3)
  r=session_replay(today,self.days[:14],101,0)
  for t in r['trades']:self.assertGreaterEqual(t['entry_at'],today[0]['timestamp']+31*60)
  self.assertEqual(r['option_performance'],'UNAVAILABLE');self.assertFalse(r['strategy_qualified'])
 def test_source_pairing_keeps_predeclared_partitions(self):
  from ops.primary_comparison import run
  raw=[b for d in self.days[:2] for b in d];names=[datetime.fromtimestamp(d[0]['timestamp'],timezone.utc).astimezone(ET).date().isoformat() for d in self.days[:2]]
  frozen={'partitions':{'development':[names[0]],'validation_retrospective':[],'evaluation_retrospective':[names[1]]}}
  r=run(raw,frozen=frozen);self.assertEqual(r['manifest']['partitions'],frozen['partitions']);self.assertFalse(r['qualified']);self.assertEqual(r['option_performance'],'UNAVAILABLE')
 def test_duplicate_or_missing_frozen_dates_are_rejected(self):
  from ops.primary_comparison import run
  raw=self.days[0];name=datetime.fromtimestamp(raw[0]['timestamp'],timezone.utc).astimezone(ET).date().isoformat()
  for values in ([name,name],['2026-10-21']):
   with self.assertRaises(ValueError):run(raw,frozen={'partitions':{'development':[],'validation_retrospective':[],'evaluation_retrospective':values}})
 def test_historical_export_cli_requires_capture_label_and_preserves_source(self):
  import tempfile,json,subprocess,sys,hashlib
  from pathlib import Path
  with tempfile.TemporaryDirectory() as d:
   source=Path(d)/'bars.json';out=Path(d)/'out.json';source.write_text(json.dumps({'bars':self.days[0],'capture_mode':'SIMULATED'}))
   cmd=[sys.executable,'-m','ops.primary_comparison','--bars-export',str(source),'--output',str(out)]
   self.assertNotEqual(subprocess.run(cmd,capture_output=True).returncode,0)
   source.write_text(json.dumps({'bars':self.days[0],'capture_mode':'HISTORICAL_DOWNLOAD'}));before=hashlib.sha256(source.read_bytes()).hexdigest();r=subprocess.run(cmd,capture_output=True)
   self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),before);self.assertFalse(json.loads(out.read_text())['qualified'])
if __name__=='__main__':unittest.main()
