import json,threading,unittest,urllib.request
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from app import Handler
from ops.data_readiness_probe import probe

class EndpointTests(unittest.TestCase):
    def test_health_route_is_bounded_read_only_no_provider(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
        try:
            with patch('ops.supervisor.status',side_effect=AssertionError('process enumeration forbidden in health HTTP')) as status,patch('core.upgrade_service.snapshot',side_effect=AssertionError('heavy provider path forbidden')):
                opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
                with opener.open('http://127.0.0.1:'+str(server.server_port)+'/healthz',timeout=2) as response:d=json.load(response)
                status.assert_not_called();self.assertTrue(d['read_only']);self.assertFalse(d['LIVE_SIGNAL_READY'])
        finally:server.shutdown();server.server_close();t.join(2)
    def test_capability_probe_uses_only_market_paths_and_preserves_refusal(self):
        calls=[];old=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
        class Provider:
            last_error=None
            def get(self,path,params):
                calls.append((path,params))
                if params['feed']!='iex':self.last_error='HTTP_403';raise RuntimeError('sensitive provider body must not be logged')
                return {'quote':{'t':old,'bp':500,'ap':500.02}}
        with patch('ops.data_readiness_probe.AlpacaProvider',Provider):r=probe()
        self.assertEqual(3,len(calls));self.assertTrue(all(p.startswith(('/v2/stocks/','/v1beta1/options/')) for p,_ in calls))
        self.assertEqual('SOURCE_TOO_OLD',r['probes'][0]['quote_diagnostics']['predicate']);self.assertFalse(r['probes'][0]['underlying_entry_fresh'])
        self.assertTrue(all(v['status']=='UNAVAILABLE' for v in r['probes'][1:]));self.assertNotIn('sensitive provider body',json.dumps(r));self.assertFalse(r['LIVE_SIGNAL_READY'])

if __name__=='__main__':unittest.main()
