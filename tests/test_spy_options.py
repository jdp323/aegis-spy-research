import tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from options.ledger import Ledger,contract
from data.spy_feed import validate_quote,fetch_quotes
from unittest.mock import patch

class OptionsTests(unittest.TestCase):
 def test_contract_and_lifecycle(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'test.sqlite';l=Ledger(path);symbol='SPY261016C00600000';t='2026-10-02T10:00:00-04:00'
   self.assertEqual(contract(symbol)['strike'],'600')
   self.assertEqual(l.record('a','BUY',symbol,2,'1.50','1.00',t),'RECORDED_USER_REPORT')
   self.assertEqual(l.record('a','BUY',symbol,2,'1.50','1.00',t),'ALREADY_RECORDED')
   l.record('b','SELL',symbol,1,'2.00','0.50',t)
   p=l.positions()[0];self.assertEqual(p['quantity'],1);self.assertEqual(p['cost_usd'],'150.50');self.assertEqual(p['realized_usd'],'49.00')
   with self.assertRaises(ValueError):l.record('c','SELL',symbol,2,'1','0',t)
   with self.assertRaises(ValueError):l.record('a','BUY',symbol,3,'1.50','1.00',t)
   with self.assertRaises(ValueError):l.record('d','BUY',symbol,True,'1','0',t)
   l.close();l=Ledger(path);self.assertEqual(l.positions()[0]['quantity'],1);l.close()
 def test_contract_rejections(self):
  for s in ['QQQ261016C00600000','SPY261332C00600000','SPY261016X00600000','SPY261016C00000000']:
   with self.assertRaises(ValueError):contract(s)
 def test_quote_quality(self):
  now=datetime.now(timezone.utc);q={'t':now.isoformat(),'bp':1,'ap':1.1}
  self.assertEqual(validate_quote(q,now)['bid'],1)
  for bad in [{**q,'bp':2},{**q,'ap':float('nan')},{**q,'t':(now-timedelta(seconds=16)).isoformat()},{**q,'t':(now+timedelta(seconds=1)).isoformat()}]:
   with self.assertRaises(ValueError):validate_quote(bad,now)
 def test_missing_credentials_never_returns_signal(self):
  with patch.dict('os.environ',{},clear=True):self.assertEqual(fetch_quotes([])['status'],'FEED_NOT_CONFIGURED')
