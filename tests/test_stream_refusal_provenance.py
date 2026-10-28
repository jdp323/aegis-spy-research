"""Synthetic provider refusals through actual stream transports; no live access."""
import asyncio,json,os,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from core.storage import Store
from data.stream import Stream
from tests.test_stream_reconnect_lifecycle import Socket

class RefusalProvenanceTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.root=Path(folder.name);self.store=Store(self.root/'state.sqlite');self.addCleanup(self.store.close)
        env=patch.dict(os.environ,{'APCA_API_KEY_ID':('synthetic-'+'key'),'APCA_API_SECRET_KEY':('synthetic-'+'secret')},clear=True)
        env.start();self.addCleanup(env.stop)
        jitter=patch('data.stream.random.random',return_value=0);jitter.start();self.addCleanup(jitter.stop)
        self.welcome=[{'T':'success','msg':'connected'}];self.auth=[{'T':'success','msg':'authenticated'}]
    def refuse(self,frames,stage,code,options=False):
        if options:self.store.put('subscriptions',['SPY261030C00600000'])
        stream=Stream(self.store,options=options,feed='sip' if options else 'iex');socket=Socket(frames,options);delays=[]
        stream.connect=lambda *a,**k:socket
        async def wait(delay):delays.append(delay);stream.stop.set()
        stream.wait=wait;asyncio.run(stream.run())
        db=sqlite3.connect((self.root/'observability.sqlite').as_uri()+'?mode=ro',uri=True)
        try:
            rows=[json.loads(r[0]) for r in db.execute("SELECT payload FROM stream_events WHERE event='PROVIDER_REJECTION'")]
            all_payloads=[r[0] for r in db.execute('SELECT payload FROM stream_events')]
        finally:db.close()
        self.assertEqual([{'provider_code':r.get('provider_code'),'reason':r.get('reason')} for r in rows],
                         [{'provider_code':code,'reason':stage}])
        self.assertEqual(delays,[300]);self.assertTrue(socket.closed)
        self.assertIsNone(self.store.get('last_market:'+stream.name))
        self.assertIsNone(self.store.get(stream.key('quote','SPY')))
        journal=json.dumps(all_payloads)+str(list(self.store.db.execute('SELECT payload FROM audit')))
        self.assertNotIn('synthetic-secret',journal);self.assertNotIn('untrusted-provider-text',journal)
        return socket
    def test_greeting_connection_limit_preserved_without_sending_credentials(self):
        socket=self.refuse([[{'T':'error','code':406,'msg':'untrusted-provider-text'}]],'GREETING',406)
        self.assertEqual(socket.sent,[])
    def test_auth_connection_limit_preserved_without_subscription(self):
        socket=self.refuse([self.welcome,[{'T':'error','code':406,'msg':'untrusted-provider-text synthetic-secret'}]],'AUTHENTICATION',406)
        self.assertEqual([r['action'] for r in socket.sent],['auth'])
    def test_binary_opra_auth_refusal_remains_distinct(self):
        socket=self.refuse([self.welcome,[{'T':'error','code':409,'msg':'untrusted-provider-text'}]],'AUTHENTICATION',409,True)
        self.assertEqual([r['action'] for r in socket.sent],['auth'])
    def test_stream_subscription_error_retains_stage_and_code(self):
        socket=self.refuse([self.welcome,self.auth,[{'T':'error','code':405,'msg':'untrusted-provider-text'}]],'STREAM',405)
        self.assertEqual([r['action'] for r in socket.sent],['auth','subscribe'])
    def test_boolean_provider_code_is_unknown_not_numeric_one(self):
        self.refuse([self.welcome,[{'T':'error','code':True,'msg':'untrusted-provider-text'}]],'AUTHENTICATION',None)

if __name__=='__main__':unittest.main()
