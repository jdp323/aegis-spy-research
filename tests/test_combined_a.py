import unittest,tempfile,struct
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from core.storage import Store
from data.stream import Stream
from core.signals import quote_valid
from data.clock_health import measure,decode_offset
from core.simple_config import validate_new
class CombinedClockTests(unittest.TestCase):
 def test_skew_boundary_and_persisted_source_watermark(self):
  with tempfile.TemporaryDirectory() as tmp:
   s=Store(Path(tmp)/'s.sqlite');now=datetime(2026,10,8,15,tzinfo=timezone.utc)
   try:
    stream=Stream(s,feed='iex',max_future_skew_seconds=2)
    with patch('data.stream.iso',return_value=now.isoformat()):
     q={'T':'q','S':'SPY','bp':600,'ap':600.1,'t':(now+timedelta(seconds=2)).isoformat()}
     self.assertTrue(stream.ingest(q));self.assertEqual(stream.last_source[('SPY','q')],now+timedelta(seconds=2))
     stored=s.get('research_quote:SPY:iex');self.assertTrue(quote_valid(stored,now));self.assertEqual(stored['source_timestamp'],q['t'])
     self.assertFalse(stream.ingest({**q,'t':(now+timedelta(seconds=2.000001)).isoformat()}));self.assertEqual(s.get('research_quote:SPY:iex'),stored)
   finally:s.close()
 def test_ntp_fake_and_bad_response(self):
  def exchange(request):
   p=bytearray(48);p[0]=0x24;p[1]=2;p[24:32]=request[40:48]
   for o,t in ((32,1001.1),(40,1001.1)):p[o:o+8]=struct.pack('!II',int(t)+2208988800,int((t-int(t))*2**32))
   return bytes(p)
  r=measure(exchange=exchange,clock=iter([1000.,1000.2]).__next__);self.assertEqual(r['state'],'MEASURED');self.assertAlmostEqual(r['offset_seconds'],1,places=5)
  self.assertEqual(measure(exchange=lambda r:b'bad',clock=iter([1000.,1000.2]).__next__)['state'],'UNAVAILABLE')
 def test_config_closed_and_bounds(self):
  for value in (-.1,5.1,True,float('nan')):
   with self.assertRaises(ValueError):validate_new({'max_future_skew_seconds':value})
  self.assertEqual(validate_new({'max_future_skew_seconds':0})['max_future_skew_seconds'],0)
