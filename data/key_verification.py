"""One bounded read-only IEX authentication probe; never log response bodies or keys."""
import json,urllib.request,urllib.error

def verify(keys,transport=None):
    request=urllib.request.Request('https://data.alpaca.markets/v2/stocks/SPY/quotes/latest?feed=iex',
        headers={'APCA-API-KEY-ID':keys['APCA_API_KEY_ID'],'APCA-API-SECRET-KEY':keys['APCA_API_SECRET_KEY']})
    try:
        with (transport or urllib.request.urlopen)(request,timeout=10) as response:
            if response.status!=200:return 'ACCESS_UNVERIFIED'
            body=response.read(65536)
            if len(body)>=65536:return 'ACCESS_UNVERIFIED'
            payload=json.loads(body)
            if not isinstance(payload,dict) or not isinstance(payload.get('quote'),dict):return 'ACCESS_UNVERIFIED'
            # Acceptance verifies credentials/access, not freshness or strategy readiness.
            return 'AUTHENTICATED_IEX'
    except urllib.error.HTTPError as error:
        return 'AUTHENTICATION_REJECTED' if error.code==401 else 'ACCESS_UNVERIFIED'
    except Exception:return 'ACCESS_UNVERIFIED'
