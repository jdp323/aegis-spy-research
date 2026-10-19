import unittest
import json
import threading
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer
from app import Handler
from datetime import datetime, timezone
from core.service import market, snapshot

class AppTests(unittest.TestCase):
    def test_weekend(self):
        self.assertEqual(market(datetime(2026,10,4,16,tzinfo=timezone.utc))['status'],'CLOSED')
    def test_holiday(self):
        self.assertEqual(market(datetime(2026,10,12,16,tzinfo=timezone.utc))['status'],'CLOSED')
    def test_early_close(self):
        self.assertEqual(market(datetime(2026,12,24,17,59,tzinfo=timezone.utc))['status'],'REGULAR_SESSION')
        self.assertEqual(market(datetime(2026,12,24,18,tzinfo=timezone.utc))['status'],'OUTSIDE_REGULAR_SESSION')
    def test_future_year_fails_closed(self):
        self.assertEqual(market(datetime(2027,1,4,16,tzinfo=timezone.utc))['status'],'CALENDAR_REFRESH_REQUIRED')
    def test_historical_account_not_ready(self):
        s=snapshot(datetime(2026,10,4,16,tzinfo=timezone.utc))
        self.assertFalse(s['account']['fresh']);self.assertFalse(s['live_execution_enabled'])
        self.assertEqual(s['strategies'], {})
    def test_dst_regular_session(self):
        self.assertEqual(market(datetime(2026,11,2,14,29,tzinfo=timezone.utc))['status'],'OUTSIDE_REGULAR_SESSION')
        self.assertEqual(market(datetime(2026,11,2,14,30,tzinfo=timezone.utc))['status'],'REGULAR_SESSION')

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url='http://127.0.0.1:'+str(cls.server.server_port)
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def test_status_is_allowlisted(self):
        with urllib.request.urlopen(self.url+'/api/status') as r:
            s=json.load(r)
            self.assertFalse(s['live_execution_enabled'])
            self.assertNotIn('chat_id',str(s));self.assertNotIn('token',str(s))
    def test_private_paths_and_writes_blocked(self):
        for path in ['/monitoring/vault.py','/../work/aegis_private/telegram.dpapi','/risk/control_v2.sqlite']:
            with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(self.url+path)
            self.assertEqual(e.exception.code,404)
        with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(urllib.request.Request(self.url+'/api/status',data=b'{}'))
        self.assertEqual(e.exception.code,501)
    def test_untrusted_host_blocked(self):
        request=urllib.request.Request(self.url+'/api/status',headers={'Host':'untrusted.example'})
        with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(request)
        self.assertEqual(e.exception.code,403)

if __name__=='__main__':unittest.main()
