"""Synthetic lifecycle tests: never connect to a provider or use real credentials."""
import asyncio,json,os,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
from core.storage import Store
from data.stream import Stream,encode,decode

class Socket:
    def __init__(self,frames,options=False):self.frames=iter(frames);self.options=options;self.sent=[];self.closed=False
    async def __aenter__(self):return self
    async def __aexit__(self,*args):self.closed=True
    async def send(self,payload):self.sent.append(decode(payload,self.options))
    async def recv(self):
        frame=next(self.frames)
        if isinstance(frame,BaseException):raise frame
        if callable(frame):frame=frame()
        return encode(frame,self.options)

class ReconnectLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.store=Store(Path(self.folder.name)/'fixture.sqlite');self.addCleanup(self.store.close)
        self.env=patch.dict(os.environ,{'APCA_API_KEY_ID':('synthetic-' + 'key'),'APCA_API_SECRET_KEY':('synthetic-' + 'secret')},clear=True)
        self.env.start();self.addCleanup(self.env.stop)
        self.jitter=patch('data.stream.random.random',return_value=0);self.jitter.start();self.addCleanup(self.jitter.stop)
        self.welcome=[{'T':'success','msg':'connected'}];self.auth=[{'T':'success','msg':'authenticated'}]
    def quote(self,symbol='SPY',bid=600):return [{'T':'q','S':symbol,'bp':bid,'ap':bid+1,'t':datetime.now(timezone.utc).isoformat()}]
    def run_stream(self,stream):asyncio.run(stream.run())
    def test_disconnect_reauthenticates_and_recovers_fresh_payload(self):
        stream=Stream(self.store);urls=[];delays=[]
        first=Socket([self.welcome,self.auth,self.quote(),ConnectionError('synthetic-secret must not enter logs')])
        def finish():stream.stop.set();return self.quote(bid=602)
        second=Socket([self.welcome,self.auth,finish]);sockets=iter([first,second])
        def connector(url,**kwargs):urls.append(url);return next(sockets)
        async def wait(delay):delays.append(delay)
        stream.connect=connector;stream.wait=wait;self.run_stream(stream)
        self.assertEqual(delays,[2]);self.assertEqual(urls,['wss://stream.data.alpaca.markets/v2/sip']*2)
        for socket in (first,second):
            self.assertTrue(socket.closed);self.assertEqual([p['action'] for p in socket.sent],['auth','subscribe'])
            self.assertEqual(socket.sent[1]['quotes'],['SPY']);self.assertEqual(socket.sent[1]['bars'],['SPY'])
        self.assertEqual(self.store.get('quote:SPY')['payload']['bid'],602)
        self.assertIsNotNone(self.store.get('last_market:sip'))
        self.assertEqual(self.store.get('stream:sip')['state'],'STOPPED')
        journal=str([r[0] for r in self.store.db.execute('SELECT payload FROM audit')])
        self.assertNotIn(('synthetic-' + 'secret'),journal);self.assertIn('ConnectionError',journal)
    def test_transport_failure_uses_bounded_exponential_backoff(self):
        stream=Stream(self.store);delays=[]
        def connector(*args,**kwargs):raise ConnectionError('offline')
        async def wait(delay):
            delays.append(delay)
            if len(delays)==10:stream.stop.set()
        stream.connect=connector;stream.wait=wait;self.run_stream(stream)
        self.assertEqual(delays,[2,4,8,16,32,64,128,256,256,256])
        self.assertIsNone(self.store.get('last_market:sip'))
    def test_opra_binary_reconnect_tracks_current_subscriptions(self):
        old='SPY261009C00775000';new='SPY261009P00775000'
        self.store.put('subscriptions',[old]);stream=Stream(self.store,True);calls=[]
        first=Socket([self.welcome,self.auth,ConnectionError('offline')],True)
        def finish():stream.stop.set();return self.quote(new,bid=2)
        second=Socket([self.welcome,self.auth,finish],True);sockets=iter([first,second])
        def connector(url,**kwargs):calls.append((url,kwargs));return next(sockets)
        async def wait(delay):self.store.put('subscriptions',[new])
        stream.connect=connector;stream.wait=wait;self.run_stream(stream)
        self.assertEqual(first.sent[1]['quotes'],[old]);self.assertEqual(second.sent[1]['quotes'],[new])
        self.assertNotIn('bars',second.sent[1])
        self.assertTrue(all(url.endswith('/v1beta1/opra') for url,_ in calls))
        self.assertTrue(all(k['additional_headers']=={'Content-Type':'application/msgpack'} for _,k in calls))
        self.assertIsNotNone(self.store.get('last_market:opra'))
        self.assertIsNone(self.store.get('quote:'+old))
    def test_idle_timeout_and_control_frames_do_not_reset_watchdog(self):
        stream=Stream(self.store);states=[];original=stream.status
        def status(state,**extra):states.append(state);original(state,**extra)
        def finish():stream.stop.set();return [{'T':'subscription','quotes':['SPY']}]
        socket=Socket([self.welcome,self.auth,asyncio.TimeoutError(),finish])
        stream.status=status;stream.connect=lambda *a,**k:socket;self.run_stream(stream)
        self.assertIn('CONNECTED_IDLE',states);self.assertIsNone(self.store.get('last_market:sip'))
        self.assertTrue(socket.closed);self.assertEqual(states[-1],'STOPPED')
    def test_opra_entitlement_rejection_never_downgrades(self):
        self.store.put('subscriptions',['SPY261009C00775000']);stream=Stream(self.store,True);urls=[];delays=[]
        socket=Socket([self.welcome,[{'T':'error','code':409,'msg':'insufficient subscription'}]],True)
        def connector(url,**kwargs):urls.append(url);return socket
        async def wait(delay):delays.append(delay);stream.stop.set()
        stream.connect=connector;stream.wait=wait;self.run_stream(stream)
        self.assertEqual(delays,[300]);self.assertEqual(urls,['wss://stream.data.alpaca.markets/v1beta1/opra'])
        self.assertEqual([p['action'] for p in socket.sent],['auth'])
        self.assertIsNone(self.store.get('last_market:opra'));self.assertTrue(socket.closed)

if __name__=='__main__':unittest.main()
