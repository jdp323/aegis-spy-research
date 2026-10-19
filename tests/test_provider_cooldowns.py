"""Read-only REST boundary validation; synthetic keys, clocks and HTTP only."""
import io,json,unittest
from email.message import Message
from unittest.mock import patch
from urllib.error import HTTPError
from data.providers import AlpacaProvider

class ProviderCooldownTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict('os.environ',{'APCA_API_KEY_ID':('fixture-' + 'key'),'APCA_API_SECRET_KEY':('fixture-' + 'secret')},clear=True)
        self.env.start();self.addCleanup(self.env.stop)
        self.clock=patch('data.providers.time.monotonic',return_value=100)
        self.mock_clock=self.clock.start();self.addCleanup(self.clock.stop)

    def error(self,code,retry=None):
        headers=Message()
        if retry is not None:headers['Retry-After']=retry
        return HTTPError('https://data.alpaca.markets/fixture',code,'fixture-secret must not escape',headers,None)

    def test_rate_limit_retry_after_is_bounded_and_repeated_calls_are_suppressed(self):
        for value,delay in [('1',60),('2000',900),('invalid',60),(None,60)]:
            with self.subTest(retry=value):
                provider=AlpacaProvider()
                with patch('data.providers.urllib.request.urlopen',side_effect=self.error(429,value)) as get:
                    with self.assertRaisesRegex(RuntimeError,'^HTTP_429$'):
                        provider.get('/v2/stocks/SPY/quotes/latest',{'feed':'sip'})
                    self.assertEqual(provider.retry_at,100+delay)
                    with self.assertRaisesRegex(RuntimeError,'^RATE_LIMIT_COOLDOWN$'):
                        provider.get('/v1beta1/options/quotes/latest',{'feed':'opra'})
                    self.assertEqual(get.call_count,1)
                    self.assertNotIn(('fixture-' + 'secret'),str(provider.health()))

    def test_auth_and_permission_denials_keep_five_minute_cooldown(self):
        for code in (401,403):
            with self.subTest(code=code):
                provider=AlpacaProvider()
                with patch('data.providers.urllib.request.urlopen',side_effect=self.error(code)) as get:
                    quote=provider.get_underlying_quote()
                    self.assertEqual(quote.quality,'FEED_DISCONNECTED')
                    self.assertEqual(provider.retry_at,400)
                    self.assertEqual(provider.health()['last_error'],'HTTP_'+str(code))
                    self.assertIn('feed=sip',get.call_args.args[0].full_url)
                    provider.get_option_quote('SPY261009C00600000')
                    self.assertEqual(get.call_count,1)
                    self.assertNotIn(('fixture-' + 'secret'),quote.reason)

    def test_retry_boundary_recovers_and_clears_error_without_feed_substitution(self):
        provider=AlpacaProvider()
        with patch('data.providers.urllib.request.urlopen',side_effect=self.error(403)):
            provider.get_underlying_quote()
        self.mock_clock.return_value=399.999
        with patch('data.providers.urllib.request.urlopen') as get:
            with self.assertRaisesRegex(RuntimeError,'RATE_LIMIT_COOLDOWN'):
                provider.get('/v2/stocks/SPY/quotes/latest',{'feed':'sip'})
            get.assert_not_called()
        self.mock_clock.return_value=400
        with patch('data.providers.urllib.request.urlopen',return_value=io.BytesIO(json.dumps({'fixture':'ok'}).encode())) as get:
            result=provider.get('/v2/stocks/SPY/quotes/latest',{'feed':'sip'})
        self.assertEqual(result,{'fixture':'ok'})
        self.assertIsNone(provider.health()['last_error'])
        self.assertEqual(provider.health()['retry_after_seconds'],0)
        self.assertIn('feed=sip',get.call_args.args[0].full_url)
        self.assertEqual(provider.health()['entitlement'],'UNVERIFIED_UNTIL_RESPONSE')

    def test_unconfigured_pair_never_attempts_http(self):
        with patch.dict('os.environ',{},clear=True),patch('data.providers.urllib.request.urlopen') as get:
            provider=AlpacaProvider()
            self.assertEqual(provider.get_underlying_quote().quality,'FEED_NOT_CONFIGURED')
            provider.get_bars();provider.get_option_chain()
            get.assert_not_called()

    def test_timeout_is_fail_closed_and_raw_exception_is_not_returned(self):
        with patch('data.providers.urllib.request.urlopen',side_effect=TimeoutError(('fixture-' + 'secret'))):
            quote=AlpacaProvider().get_underlying_quote()
        self.assertEqual(quote.quality,'FEED_DISCONNECTED')
        self.assertNotIn(('fixture-' + 'secret'),str(quote))
        self.assertEqual(quote.payload,{})

if __name__=='__main__':unittest.main()
