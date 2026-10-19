import io,json,tempfile,unittest
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from data.research_inputs import ResearchInputs,fresh_headlines
from data.providers import AlpacaProvider
from core.readiness import evaluate,text_for

NOW=datetime(2026,10,6,21,tzinfo=timezone.utc)
SYMBOL='SPY261009C00600000'
def article():
    return {'id':1,'symbols':['SPY'],'headline':'Sample research headline','created_at':(NOW-timedelta(minutes=20)).isoformat(),
            'updated_at':(NOW-timedelta(minutes=19)).isoformat(),'url':'https://example.test/article?tracking=fixture'}
def bar():
    return {'t':'2026-10-06T14:00:00Z','o':1,'h':1.2,'l':.9,'c':1.1,'v':10}

class ResearchInputTests(unittest.TestCase):
    def test_headlines_success_does_not_establish_complete_calendar_or_signal(self):
        calls=[]
        def transport(path,params):calls.append((path,params));return {'news':[article()]}
        r=ResearchInputs(transport).headlines(NOW)
        self.assertEqual(r['quality'],'DATA_OK');self.assertFalse(r['coverage_complete']);self.assertFalse(r['actionable'])
        self.assertEqual(r['articles'][0]['url'],'https://example.test/article')
        self.assertEqual(calls[0][0],'/v1beta1/news');self.assertEqual(calls[0][1]['symbols'],'SPY')
        self.assertEqual(calls[0][1]['include_content'],'false')
    def test_invalid_news_fails_closed_without_payload_or_exception_leak(self):
        for changes in ({'updated_at':(NOW+timedelta(seconds=1)).isoformat()},{'symbols':['QQQ']},{'id':True},
                        {'url':'https://secret:password@example.test/article'},{'headline':None}):
            with self.subTest(changes=changes):
                r=ResearchInputs(lambda p,q:{'news':[{**article(),**changes}]}).headlines(NOW)
                self.assertEqual(r['quality'],'DATA_INCOMPLETE');self.assertEqual(r['articles'],[])
                self.assertNotIn('password',str(r))
    def test_duplicate_articles_and_bad_container_rejected(self):
        for rows in ([article(),article()],None,{}):
            self.assertEqual(ResearchInputs(lambda p,q:{'news':rows}).headlines(NOW)['quality'],'DATA_INCOMPLETE')
    def test_empty_news_is_not_proof_of_no_risk(self):
        r=ResearchInputs(lambda p,q:{'news':[]}).headlines(NOW)
        self.assertEqual(r['quality'],'DATA_OK');self.assertFalse(r['coverage_complete'])
    def test_headlines_age_and_future_check(self):
        r=ResearchInputs(lambda p,q:{'news':[article()]}).headlines(NOW)
        self.assertEqual(fresh_headlines(r,NOW+timedelta(seconds=601))['quality'],'DATA_STALE')
        self.assertEqual(fresh_headlines(r,NOW-timedelta(seconds=1))['quality'],'DATA_INVALID')
    def test_news_permission_state_is_separate_from_history(self):
        inputs=ResearchInputs(lambda p,q:{})
        inputs.news_client.retry_at=float('inf');inputs.news_client.last_error='HTTP_403'
        r=inputs.historical_option_bars(SYMBOL,NOW-timedelta(hours=8),NOW-timedelta(hours=1),NOW)
        self.assertNotEqual(r['reason'],'HTTP_403');self.assertEqual(inputs.history_client.retry_at,0)
    def test_history_explicit_feed_window_and_non_quote_status(self):
        calls=[]
        def transport(path,params):calls.append((path,params));return {'bars':{SYMBOL:[bar()]}}
        r=ResearchInputs(transport).historical_option_bars(SYMBOL,NOW-timedelta(hours=8),NOW-timedelta(hours=1),NOW)
        self.assertEqual(r['quality'],'DATA_OK');self.assertFalse(r['executable_quote_dataset']);self.assertFalse(r['strategy_validated'])
        self.assertNotIn('feed',calls[0][1]);self.assertEqual(calls[0][0],'/v1beta1/options/bars')
        self.assertEqual(r['feed'],'PROVIDER_HISTORICAL_TRADE_BARS')
    def test_recent_naive_and_excess_history_rejected_before_http(self):
        calls=[];p=ResearchInputs(lambda p,q:calls.append(p))
        for start,end in ((NOW-timedelta(hours=1),NOW),(NOW-timedelta(days=8),NOW-timedelta(minutes=20)),
                          (NOW.replace(tzinfo=None)-timedelta(hours=1),NOW-timedelta(minutes=20))):
            with self.assertRaises(ValueError):p.historical_option_bars(SYMBOL,start,end,NOW)
        self.assertEqual(calls,[])
    def test_missing_or_invalid_history_never_becomes_usable(self):
        for rows in ([],[{**bar(),'h':.5}],[{**bar(),'v':True}],[{**bar(),'t':'2026-10-06T14:00:00.1Z'}],[bar(),bar()]):
            r=ResearchInputs(lambda p,q:{'bars':{SYMBOL:rows}}).historical_option_bars(SYMBOL,NOW-timedelta(hours=8),NOW-timedelta(hours=1),NOW)
            self.assertEqual(r['quality'],'DATA_INCOMPLETE');self.assertFalse(r['executable_quote_dataset'])
    def test_pagination_cap_and_replayed_token_fail_closed(self):
        calls=[]
        def transport(path,params):
            calls.append(params);return {'bars':{SYMBOL:[]},'next_page_token':'same'}
        r=ResearchInputs(transport).historical_option_bars(SYMBOL,NOW-timedelta(hours=8),NOW-timedelta(hours=1),NOW)
        self.assertEqual(len(calls),2);self.assertEqual(r['quality'],'DATA_INCOMPLETE')
    def test_discovery_discards_indicative_prices(self):
        raw={'snapshots':{SYMBOL:{'latestQuote':{'bp':999,'ap':1000},'greeks':{'delta':.5}}}}
        r=ResearchInputs(lambda p,q:raw).discover_contracts(600,NOW)
        self.assertEqual(r['quality'],'DATA_OK');self.assertTrue(r['prices_discarded'])
        self.assertNotIn('latestQuote',str(r));self.assertNotIn('greeks',str(r));self.assertFalse(r['live_ready'])
    def test_discovery_wrong_terms_rejected(self):
        for symbol in ('QQQ261009C00600000','SPY261005C00600000','SPY261009C00800000'):
            r=ResearchInputs(lambda p,q:{'snapshots':{symbol:{}}}).discover_contracts(600,NOW)
            self.assertEqual(r['quality'],'DATA_INCOMPLETE');self.assertEqual(r['contracts'],[])
    def test_bounded_http_body_and_non_object_response(self):
        with patch.dict('os.environ',{'APCA_API_KEY_ID':'fixture','APCA_API_SECRET_KEY':'fixture'}):
            for payload in (b'x'*(2*1024*1024+1),b'[]'):
                with patch('data.providers.urllib.request.urlopen',return_value=io.BytesIO(payload)):
                    with self.assertRaises(ValueError):AlpacaProvider().get('/v1beta1/news',{})
    def test_dynamic_readiness_removes_satisfied_checks_without_promoting(self):
        data={'live_trend':{'status':'LIVE_TREND'},'data_availability':{'options':'DATA_OK'},
              'selection':{'best_contract':{'symbol':SYMBOL}},'news':{'quality':'DATA_OK','risk':'NORMAL'},'risk':{'ready':True}}
        r=evaluate(data,dataset={'structural_valid':True})
        self.assertEqual([b['code'] for b in r['blockers']],['STRATEGY']);self.assertFalse(r['live_ready'])
        self.assertNotIn('OPTION_DATA',text_for(r))
    def test_partial_news_and_risk_not_silently_promoted(self):
        r=evaluate({'news_headlines':{'quality':'DATA_OK'},'risk':{'ready':False,'reasons':['UNCONFIGURED_LIMIT']}})
        self.assertIn('Headlines available',text_for(r));self.assertIn('UNCONFIGURED_LIMIT',text_for(r));self.assertFalse(r['live_ready'])
    def test_history_sampler_preserves_two_sides_and_does_not_make_quotes(self):
        from pathlib import Path
        from backtesting.history_sampler import collect
        class QuoteClient:
            def get(self,path,params):return {'quote':{'bp':599.9,'ap':600.1,'t':NOW.isoformat()}}
        def transport(path,params):
            if 'snapshots' in path:
                side='C' if params['type']=='call' else 'P'
                return {'snapshots':{'SPY261009'+side+'00600000':{}}}
            return {'bars':{params['symbols']:[bar()]}}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);r=collect(ResearchInputs(transport),NOW,root,QuoteClient())
            self.assertEqual(r['status'],'TRADE_BAR_SAMPLES_COLLECTED')
            self.assertEqual([p['type'] for p in r['history']],['call','put']);self.assertFalse(r['executable_quote_dataset'])
            self.assertEqual(len(list(root.rglob('manifest.json'))),1)
            self.assertFalse((root/'research/option_dataset_manifest.json').exists())
    def test_history_window_obeys_early_closes_and_unsupported_year(self):
        from backtesting.history_sampler import window
        self.assertEqual(window(datetime(2026,11,27,19,tzinfo=timezone.utc))[1].hour,13)
        self.assertIsNotNone(window(datetime(2027,2,3,21,tzinfo=timezone.utc)))
        self.assertIsNone(window(datetime(2028,2,3,21,tzinfo=timezone.utc)))

if __name__=='__main__':unittest.main()
