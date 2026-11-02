import unittest
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from core.provider_policy import allow_alpaca,PolicyRefusal,RequestBudget,runtime_streams,validate_free_policy,capability_record
from data.providers import AlpacaProvider


class FreeProviderTests(unittest.TestCase):
    def test_live_allowlist_and_no_implicit_paid_or_indicative_feed(self):
        self.assertTrue(allow_alpaca('/v2/stocks/SPY/quotes/latest',{'feed':'iex'}))
        self.assertTrue(allow_alpaca('/v2/stocks/SPY/bars',{'feed':'iex'}))
        self.assertTrue(allow_alpaca('/v1beta1/news',{}))
        for path,params in [('/v2/stocks/SPY/quotes/latest',{'feed':'sip'}),('/v2/stocks/SPY/quotes/latest',{}),('/v1beta1/options/snapshots/SPY',{'feed':'opra'}),('/v1beta1/options/snapshots/SPY',{'feed':'indicative'}),('/v2/account',{})]:
            with self.subTest(path=path,params=params),self.assertRaises(PolicyRefusal):allow_alpaca(path,params)

    def test_delayed_sip_explicit_end_and_separate_purpose_only(self):
        now=datetime(2026,11,2,15,tzinfo=timezone.utc)
        for minutes,allowed in [(15,True),(16,True),(14,False)]:
            params={'feed':'sip','end':(now-timedelta(minutes=minutes)).isoformat()}
            if allowed:self.assertTrue(allow_alpaca('/v2/stocks/SPY/bars',params,'HISTORICAL_RESEARCH',now))
            else:
                with self.assertRaises(PolicyRefusal):allow_alpaca('/v2/stocks/SPY/bars',params,'HISTORICAL_RESEARCH',now)
            with self.assertRaises(PolicyRefusal):allow_alpaca('/v2/stocks/SPY/bars',params,'RESEARCH',now)
        for params in ({'feed':'sip'},{'feed':'sip','end':'2026-01-01T10:00:00'}):
            with self.assertRaises(PolicyRefusal):allow_alpaca('/v2/stocks/SPY/bars',params,'HISTORICAL_RESEARCH',now)

    def test_policy_precedes_network_and_existing_credential_access(self):
        calls=[];p=AlpacaProvider(lambda *args:calls.append(args) or {},enforce_free=True)
        with self.assertRaises(PolicyRefusal):p.get('/v2/stocks/SPY/quotes/latest',{'feed':'sip'})
        self.assertEqual(calls,[])
        p.get('/v2/stocks/SPY/quotes/latest',{'feed':'iex'});self.assertEqual(len(calls),1)
        with self.assertRaises(ValueError):AlpacaProvider(enforce_free=False)

    def test_capability_probe_is_explicit_and_bounded(self):
        p=AlpacaProvider(lambda *args:{},enforce_free=True,purpose='CAPABILITY_PROBE')
        for feed in ('iex','sip'):p.get('/v2/stocks/SPY/quotes/latest',{'feed':feed})
        p.get('/v1beta1/options/snapshots/SPY',{'feed':'opra','limit':1})
        with self.assertRaises(PolicyRefusal):p.get('/v2/stocks/SPY/quotes/latest',{'feed':'iex'})
        with self.assertRaises(PolicyRefusal):allow_alpaca('/v1beta1/options/snapshots/SPY',{'feed':'opra','limit':100},'CAPABILITY_PROBE')

    def test_runtime_stream_policy_does_not_retry_unestablished_entitlements(self):
        self.assertEqual(runtime_streams({}),[('iex',False)])
        self.assertEqual(runtime_streams({'option_data_provider':'questrade'}),[('iex',False)])
        for config in ({'operating_mode':'PAID'},{'paid_api_enabled':True},{'paid_model_enabled':True},{'option_data_provider':'TRADIER'}):
            with self.assertRaises(ValueError):validate_free_policy(config)

    def test_quota_and_concurrency_are_no_wait_and_reset_without_paid_fallback(self):
        clock=[0];b=RequestBudget(2,1,lambda:clock[0]);b.enter()
        with self.assertRaises(PolicyRefusal):b.enter()
        b.leave();b.enter();b.leave()
        with self.assertRaises(PolicyRefusal):b.enter()
        clock[0]=60;b.enter();b.leave();self.assertEqual(b.active,0)

    def test_403_does_not_invent_cause_or_greek_and_chain_capability(self):
        result=capability_record({'at':'2026-11-01T22:00:00+00:00','probes':[{'feed':'SIP','status':'UNAVAILABLE','provider_error_class':'HTTP_403'}]},credentials_configured=True)
        self.assertEqual(result['capabilities']['SIP']['access'],'REFUSED')
        self.assertEqual(result['capabilities']['OPRA']['access'],'UNKNOWN')
        self.assertEqual(result['capabilities']['SIP']['greeks'],'UNKNOWN')
        self.assertIn('UNKNOWN',result['capabilities']['SIP']['refusal_cause'])
        self.assertFalse(result['live_signal_ready']);self.assertEqual(result['option_performance'],'NOT_MEASURED')

    def test_http_429_retains_cooldown_no_sip_or_indicative_retry(self):
        import urllib.error
        def refused(*args):raise urllib.error.HTTPError('https://data.alpaca.markets',429,'rate limit',{'Retry-After':'600'},None)
        p=AlpacaProvider(refused,enforce_free=True)
        with self.assertRaisesRegex(RuntimeError,'HTTP_429'):p.get('/v2/stocks/SPY/quotes/latest',{'feed':'iex'})
        self.assertGreater(p.retry_at,0)
        with self.assertRaisesRegex(RuntimeError,'RATE_LIMIT_COOLDOWN'):p.get('/v2/stocks/SPY/quotes/latest',{'feed':'iex'})


if __name__=='__main__':unittest.main()
