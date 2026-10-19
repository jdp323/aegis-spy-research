"""Synthetic malformed transport/auth/subscription recovery; no live connections."""
import asyncio
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import test_stream_reconnect_lifecycle as lifecycle
from core.storage import Store
from data.stream import Stream

class BadJsonSocket(lifecycle.Socket):
    async def recv(self):
        if len(self.sent)==2:return '{synthetic-private-provider-text'
        return await super().recv()

class ProtocolRecoveryTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.store=Store(Path(folder.name)/'fixture.sqlite');self.addCleanup(self.store.close)
        env=patch.dict(os.environ,{'APCA_API_KEY_ID':('synthetic-' + 'key'),'APCA_API_SECRET_KEY':('synthetic-' + 'secret')},clear=True)
        env.start();self.addCleanup(env.stop)
        jitter=patch('data.stream.random.random',return_value=0);jitter.start();self.addCleanup(jitter.stop)
        self.welcome=[{'T':'success','msg':'connected'}]
        self.auth=[{'T':'success','msg':'authenticated'}]

    def recover(self,first,feed='sip'):
        stream=Stream(self.store,feed=feed);delays=[];urls=[]
        def finish():
            stream.stop.set()
            return [{'T':'q','S':'SPY','bp':600,'ap':601,'t':datetime.now(timezone.utc).isoformat()}]
        second=lifecycle.Socket([self.welcome,self.auth,finish]);sockets=iter([first,second])
        def connect(url,**kwargs):urls.append(url);return next(sockets)
        async def wait(delay):delays.append(delay)
        stream.connect=connect;stream.wait=wait;asyncio.run(stream.run())
        self.assertTrue(first.closed);self.assertTrue(second.closed)
        self.assertEqual(urls,['wss://stream.data.alpaca.markets/v2/'+feed]*2)
        self.assertIsNotNone(self.store.get('last_market:'+feed))
        self.assertEqual([m['action'] for m in second.sent],['auth','subscribe'])
        journal=str([row[0] for row in self.store.db.execute('SELECT payload FROM audit')])
        self.assertNotIn(('synthetic-' + 'secret'),journal)
        self.assertNotIn('synthetic-private-provider-text',journal)
        return delays,journal

    def test_malformed_json_disconnects_and_reauthenticates_without_logging_payload(self):
        first=BadJsonSocket([self.welcome,self.auth])
        delays,journal=self.recover(first)
        self.assertEqual(delays,[2]);self.assertIn('JSONDecodeError',journal)

    def test_malformed_auth_shape_never_subscribes_before_valid_reauthentication(self):
        first=lifecycle.Socket([self.welcome,{'T':'success','msg':'authenticated'}])
        delays,journal=self.recover(first,'iex')
        self.assertEqual([m['action'] for m in first.sent],['auth'])
        self.assertEqual(delays,[2]);self.assertIn('AttributeError',journal)
        self.assertIsNone(self.store.get('last_market:sip'))
        self.assertIsNone(self.store.get('quote:SPY'))

    def test_subscription_rejection_uses_permission_cooldown_then_same_feed(self):
        first=lifecycle.Socket([self.welcome,self.auth,[{'T':'error','code':405,'msg':'synthetic-private-provider-text'}]])
        delays,journal=self.recover(first)
        self.assertEqual(delays,[300]);self.assertIn('PermissionError',journal)

    def test_partial_credentials_never_open_any_transport(self):
        self.store.put('subscriptions',['SPY261009C00775000'])
        for name,options in (('sip',False),('iex',False),('sip',True)):
            for present in ('APCA_API_KEY_ID','APCA_API_SECRET_KEY'):
                with self.subTest(feed=name,options=options,present=present),patch.dict(os.environ,{present:'synthetic-only-one-key'},clear=True):
                    stream=Stream(self.store,options=options,feed=name)
                    stream.connect=lambda *a,**k:self.fail('Partial credentials must not connect')
                    async def wait(delay):stream.stop.set()
                    stream.wait=wait;asyncio.run(stream.run())
                    self.assertEqual(self.store.get('stream:'+stream.name)['state'],'FEED_NOT_CONFIGURED')
                    self.assertIsNone(self.store.get('last_market:'+stream.name))

if __name__=='__main__':unittest.main()
