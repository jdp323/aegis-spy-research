import io,json,unittest
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from urllib.error import HTTPError
from data.spy_feed import fetch_quotes

class TransportTests(unittest.TestCase):
 def setUp(self):
  self.now=datetime(2026,10,5,14,tzinfo=timezone.utc)
  self.symbol='SPY261016C00600000'
  self.q={'t':self.now.isoformat(),'bp':1,'ap':1.1}
  self.env=patch.dict('os.environ',{'APCA_API_KEY_ID':('synthetic-' + 'key'),'APCA_API_SECRET_KEY':('synthetic-' + 'secret')},clear=True);self.env.start();self.addCleanup(self.env.stop)
 def response(self,obj):return io.BytesIO(json.dumps(obj).encode())
 def test_slow_second_request_invalidates_first_quote(self):
  clock=[self.now]
  def get(req,timeout):
   if '/stocks/' in req.full_url:return self.response({'quote':self.q})
   clock[0]+=timedelta(seconds=20)
   return self.response({'quotes':{self.symbol:{**self.q,'t':clock[0].isoformat()}}})
  with patch('data.spy_feed.urllib.request.urlopen',side_effect=get),patch('data.spy_feed.datetime') as dt:
   dt.fromisoformat.side_effect=datetime.fromisoformat;dt.now.side_effect=lambda *a:clock[0]
   r=fetch_quotes([self.symbol])
  self.assertEqual(r['status'],'FEED_UNAVAILABLE_OR_INVALID');self.assertEqual(r['quotes'],{})
 def test_access_denied_does_not_fallback(self):
  with patch('data.spy_feed.urllib.request.urlopen',side_effect=HTTPError('https://example.invalid',403,'denied',None,None)) as get:
   r=fetch_quotes([self.symbol])
  self.assertEqual(r['quotes'],{});self.assertEqual(get.call_count,1)
  self.assertIn('feed=sip',get.call_args.args[0].full_url)
 def test_recovery_after_timeout_stays_research_only(self):
  with patch('data.spy_feed.urllib.request.urlopen',side_effect=TimeoutError):self.assertEqual(fetch_quotes([])['quotes'],{})
  with patch('data.spy_feed.urllib.request.urlopen',side_effect=[self.response({'quote':self.q}),self.response({'quotes':{self.symbol:self.q}})]) as get,patch('data.spy_feed.datetime') as dt:
   dt.fromisoformat.side_effect=datetime.fromisoformat;dt.now.return_value=self.now
   r=fetch_quotes([self.symbol])
  self.assertEqual(r['status'],'FRESH_QUOTES_RESEARCH_ONLY');self.assertEqual(r['action'],'NO TRADE')
  self.assertIn('feed=opra',get.call_args.args[0].full_url)
 def test_missing_contract_discards_partial_result(self):
  with patch('data.spy_feed.urllib.request.urlopen',side_effect=[self.response({'quote':self.q}),self.response({'quotes':{}})]),patch('data.spy_feed.datetime') as dt:
   dt.fromisoformat.side_effect=datetime.fromisoformat;dt.now.return_value=self.now
   self.assertEqual(fetch_quotes([self.symbol])['quotes'],{})
