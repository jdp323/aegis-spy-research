import io,json,unittest,urllib.error
from data.key_verification import verify
KEYS={'APCA_API_KEY_ID':('synthetic-' + 'key'),'APCA_API_SECRET_KEY':('synthetic-' + 'secret')}
class Reply(io.BytesIO):
    status=200
class KeyVerificationTests(unittest.TestCase):
    def test_accepted_read_only_probe_does_not_claim_freshness(self):
        def transport(req,timeout):
            self.assertEqual(req.full_url,'https://data.alpaca.markets/v2/stocks/SPY/quotes/latest?feed=iex')
            self.assertEqual(req.get_method(),'GET');self.assertEqual(timeout,10)
            return Reply(b'{"quote":{"t":"2026-10-06T20:00:00Z"}}')
        self.assertEqual(verify(KEYS,transport),'AUTHENTICATED_IEX')
    def test_unauthorized_is_explicit_and_response_not_exposed(self):
        def transport(*a,**k):raise urllib.error.HTTPError('url',401,'secret-like-response',{},None)
        self.assertEqual(verify(KEYS,transport),'AUTHENTICATION_REJECTED')
    def test_other_denials_and_transport_errors_are_unverified(self):
        for code in (403,429,500):
            def transport(*a,**k):raise urllib.error.HTTPError('url',code,'details',{},None)
            self.assertEqual(verify(KEYS,transport),'ACCESS_UNVERIFIED')
        def transport(*a,**k):raise TimeoutError('details')
        self.assertEqual(verify(KEYS,transport),'ACCESS_UNVERIFIED')
    def test_malformed_or_oversized_data_cannot_enable_save(self):
        for payload in (b'[]',b'{}',b'{"quote":null}',b'not-json',b'x'*65536):
            with self.subTest(payload_length=len(payload)):
                self.assertEqual(verify(KEYS,lambda *a,**k:Reply(payload)),'ACCESS_UNVERIFIED')
if __name__=='__main__':unittest.main()
