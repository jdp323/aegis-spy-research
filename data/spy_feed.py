"""Read-only Alpaca SIP/OPRA quotes. Never falls back to indicative feeds."""
import json,os,urllib.request
from datetime import datetime,timezone
from options.ledger import contract

def validate_quote(q,now=None,max_age=15):
    now=now or datetime.now(timezone.utc)
    try:
        stamp=datetime.fromisoformat(q['t'].replace('Z','+00:00'))
        age=(now-stamp).total_seconds()
        bid,ask=q['bp'],q['ap']
        import math
        if type(bid) not in (int,float) or type(ask) not in (int,float) or not math.isfinite(bid) or not math.isfinite(ask) or not 0<bid<=ask:raise ValueError()
        if not 0<=age<=max_age:raise ValueError()
        return {'bid':bid,'ask':ask,'timestamp':stamp.isoformat(),'age_seconds':age}
    except (ValueError,KeyError,TypeError,OverflowError):raise ValueError('DATA INVALID: stale, future, missing or crossed quote') from None

def fetch_quotes(symbols):
    key=os.environ.get('APCA_API_KEY_ID');secret=os.environ.get('APCA_API_SECRET_KEY')
    if not key or not secret:return {'status':'FEED_NOT_CONFIGURED','action':'NO TRADE','quotes':{}}
    for s in symbols:contract(s)
    def get(url):
        req=urllib.request.Request(url,headers={'APCA-API-KEY-ID':key,'APCA-API-SECRET-KEY':secret})
        with urllib.request.urlopen(req,timeout=10) as r:return json.load(r)
    try:
        spy=get('https://data.alpaca.markets/v2/stocks/SPY/quotes/latest?feed=sip')['quote']
        raw_quotes={'SPY':spy}
        if symbols:
            from urllib.parse import urlencode
            raw=get('https://data.alpaca.markets/v1beta1/options/quotes/latest?'+urlencode({'symbols':','.join(symbols),'feed':'opra'}))['quotes']
            raw_quotes.update({s:raw[s] for s in symbols})
        # Validate the whole batch after the last network response; an earlier
        # underlying quote can become stale while option requests are pending.
        checked_at=datetime.now(timezone.utc)
        quotes={s:validate_quote(q,now=checked_at) for s,q in raw_quotes.items()}
        return {'status':'FRESH_QUOTES_RESEARCH_ONLY','action':'NO TRADE','quotes':quotes,'feeds':['sip','opra'],'note':'Quotes alone do not validate strategy, Greeks, bars, contract terms, monitor or execution.'}
    except Exception:return {'status':'FEED_UNAVAILABLE_OR_INVALID','action':'NO TRADE','quotes':{},'note':'Check entitlement/connectivity; no fallback to delayed or indicative data.'}
