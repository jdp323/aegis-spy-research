import unittest,tempfile,json
from pathlib import Path
from datetime import datetime,timezone,timedelta
from data.questrade import QuestradeProvider,origin,ALLOWED
from data.questrade_vault import Vault
NOW=datetime(2026,10,8,15,tzinfo=timezone.utc)
def crypt(b,decrypt=False):return b[::-1]
class QuestradeTests(unittest.TestCase):
 def test_cross_process_lock_serializes(self):
  import subprocess,sys
  with tempfile.TemporaryDirectory() as d:
   root=Path(__file__).parents[1];log=Path(d)/'lock.log';vault=Path(d)/'v'
   children=[subprocess.Popen([sys.executable,'-m','tests.questrade_lock_child',str(vault),str(log),str(i)],cwd=root) for i in (1,2)]
   self.assertEqual([p.wait(timeout=10) for p in children],[0,0])
   rows=log.read_text().splitlines();self.assertTrue(rows[0].startswith('enter'));self.assertEqual(rows[0][6:],rows[1][5:]);self.assertEqual(rows[2][6:],rows[3][5:])
 def test_crash_after_remote_consumption_before_persistence(self):
  with tempfile.TemporaryDirectory() as d:
   v=Vault(Path(d)/'v',crypt);v.configure('fake-fixture-refresh-only',NOW);save=v.save;calls=[]
   def fail_final(state):
    if state.get('access_token'):raise OSError('simulated disk failure')
    save(state)
   v.save=fail_final
   def remote(*a):calls.append(1);return dict(refresh_token='rotated-fixture-only',access_token='fixture-access-only',expires_in=1800,api_server='https://api01.iq.questrade.com/')
   p=QuestradeProvider(v,remote,clock=lambda:NOW)
   for _ in (1,2):
    with self.assertRaisesRegex(RuntimeError,'UNCERTAIN'):p.session()
   self.assertEqual(calls,[1]);self.assertTrue(v.load()['refresh_in_progress'])
 def test_http_429_cooldown_prevents_repeat_request(self):
  import urllib.error,time
  calls=[];p=QuestradeProvider(clock=lambda:NOW);p.session=lambda:dict(api_server='https://api01.iq.questrade.com',access_token='fixture-only');p.limit=lambda:None
  def remote(*a):calls.append(1);raise urllib.error.HTTPError('https://example.invalid',429,'rate',{'X-RateLimit-Reset':str(NOW.timestamp()+60)},None)
  p.request=remote
  with self.assertRaisesRegex(RuntimeError,'HTTP_429'):p.get('/time')
  self.assertGreater(p.retry_at-time.monotonic(),55)
  with self.assertRaisesRegex(RuntimeError,'COOLDOWN'):p.get('/time')
  self.assertEqual(calls,[1])
 def test_refresh_persisted_before_use_and_crash_journal(self):
  with tempfile.TemporaryDirectory() as d:
   v=Vault(Path(d)/'v.dpapi',crypt);v.configure('fake-refresh-fixture-only',NOW)
   calls=[]
   def fake(url,method,headers,body):
    calls.append(url);return dict(refresh_token='rotated-fixture-token',access_token='fake-access-fixture',expires_in=1800,api_server='https://api01.iq.questrade.com/')
   p=QuestradeProvider(v,fake,clock=lambda:NOW);self.assertEqual(p.session()['refresh_token'],'rotated-fixture-token');self.assertFalse(v.load()['refresh_in_progress']);p.session();self.assertEqual(len(calls),1)
   v.configure('second-fake-refresh-fixture',NOW)
   p.request=lambda *a:(_ for _ in ()).throw(OSError())
   with self.assertRaises(RuntimeError):p.session()
   self.assertEqual(v.status(NOW)['status'],'QUESTRADE_REFRESH_UNCERTAIN')
   with self.assertRaises(RuntimeError):p.session()
 def test_allowlist_and_origins(self):
  for path in ('/time','/symbols/search','/symbols/1/options','/markets/candles/1','/markets/quotes/options'):self.assertTrue(ALLOWED.fullmatch(path))
  for path in ('/accounts','/orders','/markets/quotes/../orders','//time'):self.assertFalse(ALLOWED.fullmatch(path))
  for u in ('http://api01.iq.questrade.com','https://api01.iq.questrade.com.evil.test','https://api01.iq.questrade.com/x'):
   with self.assertRaises(ValueError):origin(u)
  source=(Path(__file__).parents[1]/'data/questrade.py').read_text()
  for word in ('/accounts','/balances','/positions','/orders','/executions','/activities'):self.assertNotIn(word,source)
 def test_last_trade_time_is_not_quote_time(self):
  p=QuestradeProvider(clock=lambda:NOW)
  q=p.parse_quote('SPY261014C00500000',dict(delay=0,bidPrice=2,askPrice=2.1,lastTradeTime=NOW.isoformat(),delta=.5),True).view(NOW)
  self.assertEqual(q['quality'],'DATA_INCOMPLETE');self.assertIsNone(q['source_timestamp']);self.assertEqual(q['entitlement'],'UNVERIFIED')
  self.assertEqual(p.parse_quote('SPY',dict(delay=True,bidPrice=500,askPrice=501)).quality,'DATA_STALE')
 def test_policy_expiry_and_no_token(self):
  with tempfile.TemporaryDirectory() as d:
   v=Vault(Path(d)/'v',crypt);self.assertEqual(v.status(NOW)['status'],'QUESTRADE_NOT_CONFIGURED');v.configure('fake-token-fixture-only',NOW)
   self.assertEqual(v.status(NOW+timedelta(days=3))['status'],'QUESTRADE_TOKEN_EXPIRED')
