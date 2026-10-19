"""Injected IEX transport lifecycle checks; no real keys or network calls."""
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


class IexLifecycleTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.store = Store(Path(folder.name) / 'fixture.sqlite')
        self.addCleanup(self.store.close)
        env = patch.dict(os.environ, {
            'APCA_API_KEY_ID': ('synthetic-' + 'key'),
            'APCA_API_SECRET_KEY': ('synthetic-' + 'secret'),
        }, clear=True)
        env.start()
        self.addCleanup(env.stop)
        jitter = patch('data.stream.random.random', return_value=0)
        jitter.start()
        self.addCleanup(jitter.stop)
        self.welcome = [{'T': 'success', 'msg': 'connected'}]
        self.auth = [{'T': 'success', 'msg': 'authenticated'}]

    def quote(self, bid=600):
        return [{'T': 'q', 'S': 'SPY', 'bp': bid, 'ap': bid + 1,
                 't': datetime.now(timezone.utc).isoformat()}]

    def test_reconnect_reauthenticates_without_overwriting_sip(self):
        self.store.put('quote:SPY', {'sentinel': 'consolidated'})
        self.store.put('last_market:sip', {'sentinel': 'consolidated'})
        stream = Stream(self.store, feed='iex')
        first = lifecycle.Socket([self.welcome, self.auth, self.quote(),
                                  ConnectionError(('synthetic-' + 'secret'))])

        def finish():
            stream.stop.set()
            return self.quote(602)

        second = lifecycle.Socket([self.welcome, self.auth, finish])
        sockets = iter([first, second])
        urls, delays = [], []

        def connect(url, **kwargs):
            urls.append(url)
            self.assertEqual(kwargs['additional_headers'], {})
            return next(sockets)

        async def wait(delay):
            delays.append(delay)

        stream.connect, stream.wait = connect, wait
        asyncio.run(stream.run())
        self.assertEqual(urls, ['wss://stream.data.alpaca.markets/v2/iex'] * 2)
        self.assertEqual(delays, [2])
        for socket in (first, second):
            self.assertTrue(socket.closed)
            self.assertEqual([m['action'] for m in socket.sent], ['auth', 'subscribe'])
            for channel in ('quotes', 'trades', 'bars', 'updatedBars'):
                self.assertEqual(socket.sent[1][channel], ['SPY'])
        self.assertEqual(self.store.get('research_quote:SPY:iex')['payload']['bid'], 602)
        self.assertIsNotNone(self.store.get('last_market:iex'))
        self.assertEqual(self.store.get('quote:SPY'), {'sentinel': 'consolidated'})
        self.assertEqual(self.store.get('last_market:sip'), {'sentinel': 'consolidated'})
        journal = str([r[0] for r in self.store.db.execute('SELECT payload FROM audit')])
        self.assertNotIn(('synthetic-' + 'secret'), journal)
        self.assertIn('ConnectionError', journal)

    def test_auth_denial_cools_down_without_changing_feed(self):
        stream = Stream(self.store, feed='iex')
        socket = lifecycle.Socket([self.welcome, [{'T': 'error', 'code': 402,
                                                  'msg': 'auth failed'}]])
        urls, delays = [], []

        def connect(url, **kwargs):
            urls.append(url)
            return socket

        async def wait(delay):
            delays.append(delay)
            stream.stop.set()

        stream.connect, stream.wait = connect, wait
        asyncio.run(stream.run())
        self.assertEqual(urls, ['wss://stream.data.alpaca.markets/v2/iex'])
        self.assertEqual(delays, [300])
        self.assertEqual([m['action'] for m in socket.sent], ['auth'])
        self.assertTrue(socket.closed)
        self.assertIsNone(self.store.get('last_market:iex'))
        self.assertIsNone(self.store.get('research_quote:SPY:iex'))

    def test_idle_and_control_frames_do_not_count_as_market_recovery(self):
        stream = Stream(self.store, feed='iex')
        states = []
        original = stream.status

        def status(state, **extra):
            states.append(state)
            original(state, **extra)

        def finish():
            stream.stop.set()
            return [{'T': 'subscription', 'quotes': ['SPY']}]

        socket = lifecycle.Socket([self.welcome, self.auth, asyncio.TimeoutError(), finish])
        stream.status = status
        stream.connect = lambda *a, **k: socket
        asyncio.run(stream.run())
        self.assertIn('CONNECTED_IDLE', states)
        self.assertEqual(states[-1], 'STOPPED')
        self.assertTrue(socket.closed)
        self.assertIsNone(self.store.get('last_market:iex'))

    def test_cancellation_closes_transport_without_reconnect(self):
        stream = Stream(self.store, feed='iex')
        socket = lifecycle.Socket([self.welcome, self.auth, asyncio.CancelledError()])
        stream.connect = lambda *a, **k: socket

        async def forbidden_wait(delay):
            self.fail('Cancellation must not schedule reconnect')

        stream.wait = forbidden_wait
        asyncio.run(stream.run())
        self.assertTrue(socket.closed)
        self.assertEqual(stream.attempt, 0)
        self.assertEqual(self.store.get('stream:iex')['state'], 'STOPPED')
        self.assertIsNone(self.store.get('last_market:iex'))

    def test_unconfigured_feed_never_invokes_transport(self):
        stream = Stream(self.store, feed='iex')
        stream.connect = lambda *a, **k: self.fail('Unconfigured feed must not connect')
        delays = []

        async def wait(delay):
            delays.append(delay)
            stream.stop.set()

        stream.wait = wait
        with patch.dict(os.environ, {}, clear=True):
            asyncio.run(stream.run())
        self.assertEqual(delays, [30])
        self.assertEqual(self.store.get('stream:iex')['state'], 'FEED_NOT_CONFIGURED')
        self.assertIsNone(self.store.get('last_market:iex'))


if __name__ == '__main__':
    unittest.main()
