import unittest,tempfile,json
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from data.session_recorder import Recorder
from core.storage import Store
from ops.live_verify import sample
NOW=datetime(2026,10,8,15,tzinfo=timezone.utc)
class RecorderTests(unittest.TestCase):
 def test_record_tagged_and_revision_idempotency(self):
  with tempfile.TemporaryDirectory() as tmp:
   r=Recorder(Path(tmp)/'h.sqlite');bar={'t':(NOW-timedelta(minutes=1)).isoformat(),'o':100,'h':101,'l':99,'c':100,'v':100};self.assertEqual(r.bars([bar],'IEX',NOW),1);self.assertEqual(r.bars([bar],'IEX',NOW),0);self.assertEqual(r.bars([bar],'SIP',NOW),1);self.assertEqual(r.db.execute('SELECT count(*) FROM session_bars').fetchone()[0],2)
   self.assertFalse(r.iv_history()['iv_rank_enabled']);self.assertFalse(r.iv_history()['iv_rank_history_ready']);r.close()
 def test_indicative_isolated_chain(self):
  with tempfile.TemporaryDirectory() as tmp:
   r=Recorder(Path(tmp)/'h.sqlite');d={'provider':'fixture-indicative','feed_quality':'INDICATIVE','payload':{'contracts':{'SPY261009C00600000':{'latestQuote':{'t':NOW.isoformat()},'impliedVolatility':.2}}}};self.assertEqual(r.chain(d,600,NOW),1);self.assertEqual(r.db.execute('SELECT feed_quality FROM option_snapshots').fetchone()[0],'INDICATIVE');self.assertEqual(r.iv_history()['observed_trading_days'],1);r.close()
 def test_closed_session_no_sample_or_fake_report(self):
  with tempfile.TemporaryDirectory() as tmp:
   s=Store(Path(tmp)/'s.sqlite');self.assertEqual(sample(s,NOW.replace(hour=0))['state'],'WAITING_FOR_REGULAR_SESSION');self.assertFalse(s.db.execute("SELECT name FROM sqlite_master WHERE name='live_verify_samples'").fetchone());s.close()
 def test_actual_failed_sample_is_retained(self):
  with tempfile.TemporaryDirectory() as tmp:
   s=Store(Path(tmp)/'s.sqlite');root=Path(tmp);(root/'daily_reports').mkdir()
   with patch('ops.live_verify.ROOT',root):
    r=sample(s,NOW,crosscheck=lambda *a:{'quality':'UNAVAILABLE'});self.assertFalse(r['fresh_quote']);self.assertEqual(s.db.execute('SELECT count(*) FROM live_verify_samples').fetchone()[0],1);self.assertIn('FAIL',(root/'daily_reports/LIVE_VERIFY_2026-10-08.md').read_text(encoding='utf-8'))
   s.close()
