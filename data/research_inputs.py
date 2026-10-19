"""Authenticated research inputs, isolated from live SIP/OPRA strategy stores.

Headlines do not establish a complete economic calendar. Historical option bars
are trades, not bid/ask quotes or proof of executable simulated fills.
"""
from datetime import datetime,timezone,timedelta
from urllib.parse import urlsplit,urlunsplit
import re
from data.providers import AlpacaProvider
from data.models import stamp,finite
from options.ledger import contract

NEWS_URL='https://data.alpaca.markets/v1beta1/news'
BARS_URL='https://data.alpaca.markets/v1beta1/options/bars'
MAX_PAGES=3

def safe_url(value):
    if not isinstance(value,str) or len(value)>2048:raise ValueError('INVALID_ARTICLE_URL')
    u=urlsplit(value)
    if u.scheme!='https' or not u.hostname or u.username or u.password:raise ValueError('INVALID_ARTICLE_URL')
    return urlunsplit((u.scheme,u.netloc,u.path,'',''))

def clean_headline(value):
    if not isinstance(value,str) or not value.strip():raise ValueError('INVALID_HEADLINE')
    # Text only: neither HTML nor provider strings become code or instructions.
    return re.sub(r'[\x00-\x1f\x7f]+',' ',value).strip()[:160]

class ResearchInputs:
    def __init__(self,transport=None):
        # A denied SIP request must not block independently entitled news/history.
        self.news_client=AlpacaProvider(transport)
        self.history_client=AlpacaProvider(transport)

    def headlines(self,now=None):
        now=now or datetime.now(timezone.utc)
        out={'provider':'alpaca','data_type':'news_headlines','fetched_at':now.isoformat(),
             'source_url':NEWS_URL,'quality':'DATA_INCOMPLETE','coverage_complete':False,
             'delay_status':'UNVERIFIED','actionable':False,'articles':[],
             'note':'SPY-tagged provider headlines only; not a complete event calendar or breaking-news guarantee.'}
        try:
            raw=self.news_client.get('/v1beta1/news',{'symbols':'SPY','start':(now-timedelta(days=2)).isoformat(),
                'end':now.isoformat(),'limit':20,'sort':'desc','include_content':'false'})
            rows=raw['news']
            if not isinstance(rows,list) or len(rows)>20:raise ValueError('INVALID_NEWS_ROWS')
            articles=[];seen=set()
            for r in rows:
                if not isinstance(r,dict) or type(r.get('id')) is not int or r['id'] in seen:raise ValueError('INVALID_NEWS_ID')
                symbols=r.get('symbols')
                if not isinstance(symbols,list) or 'SPY' not in symbols:raise ValueError('INVALID_NEWS_SYMBOL')
                created=stamp(r['created_at']);updated=stamp(r['updated_at'])
                if not created<=updated<=now:raise ValueError('INVALID_NEWS_TIMESTAMP')
                articles.append({'id':r['id'],'headline':clean_headline(r['headline']),
                    'url':safe_url(r['url']),'created_at':r['created_at'],'updated_at':r['updated_at']})
                seen.add(r['id'])
            out.update(quality='DATA_OK',articles=articles,pagination_complete=not bool(raw.get('next_page_token')),
                reason='AUTHENTICATED_HEADLINE_QUERY_SUCCEEDED')
        except Exception:
            out.update(reason=self.news_client.last_error or 'HEADLINE_QUERY_UNAVAILABLE_OR_INVALID')
        return out

    def historical_option_bars(self,symbol,start,end,now=None):
        now=now or datetime.now(timezone.utc);spec=contract(symbol)
        if not isinstance(start,datetime) or not isinstance(end,datetime) or start.tzinfo is None or end.tzinfo is None:
            raise ValueError('AWARE_HISTORY_WINDOW_REQUIRED')
        if not start<end<=now-timedelta(minutes=20) or end-start>timedelta(days=7):
            raise ValueError('HISTORICAL_CUTOFF_OR_WINDOW_INVALID')
        out={'provider':'alpaca','feed':'PROVIDER_HISTORICAL_TRADE_BARS','data_type':'option_trade_bars','symbol':symbol,
             'source_url':BARS_URL,'fetched_at':now.isoformat(),'requested_start':start.isoformat(),
             'requested_end':end.isoformat(),'quality':'DATA_INCOMPLETE','bars':[],
             'pagination_complete':False,'executable_quote_dataset':False,'strategy_validated':False,
             'note':'Historical trade bars only. OHLC is not executable bid/ask; no spread, Greeks or open interest inferred.'}
        try:
            rows=[];token=None;seen_tokens=set()
            for _ in range(MAX_PAGES):
                # The documented bars endpoint has no feed selector. Never add
                # snapshot-only feed parameters or promote trade OHLC to OPRA quotes.
                params={'symbols':symbol,'timeframe':'1Min','start':start.isoformat(),
                        'end':end.isoformat(),'limit':1000,'sort':'asc'}
                if token:params['page_token']=token
                raw=self.history_client.get('/v1beta1/options/bars',params)
                data=raw['bars']
                if not isinstance(data,dict) or any(k!=symbol for k in data):raise ValueError('HISTORY_SYMBOL_MISMATCH')
                page=data.get(symbol,[])
                if not isinstance(page,list) or len(page)>1000:raise ValueError('INVALID_HISTORY_ROWS')
                rows.extend(page);token=raw.get('next_page_token')
                if not token:break
                if not isinstance(token,str) or len(token)>4096 or token in seen_tokens:raise ValueError('INVALID_PAGE_TOKEN')
                seen_tokens.add(token)
            previous=None
            for r in rows:
                if not isinstance(r,dict):raise ValueError('INVALID_BAR')
                t=stamp(r['t'])
                from core.sessions import ET
                if not start<=t<=end or t.second or t.microsecond or (previous is not None and t<=previous) or t.astimezone(ET).date().isoformat()>spec['expiry']:
                    raise ValueError('INVALID_BAR_TIMESTAMP')
                if not all(finite(r.get(k)) and r[k]>0 for k in ('o','h','l','c')) or not r['l']<=min(r['o'],r['c'])<=max(r['o'],r['c'])<=r['h']:
                    raise ValueError('INVALID_BAR_OHLC')
                if type(r.get('v')) is not int or r['v']<0:raise ValueError('INVALID_BAR_VOLUME')
                previous=t
            out.update(bars=rows,pagination_complete=not bool(token),
                quality='DATA_OK' if rows and not token else 'DATA_INCOMPLETE',
                reason='HISTORICAL_TRADE_BARS_ONLY' if rows else 'NO_HISTORICAL_BARS_RETURNED')
        except Exception:
            out.update(reason=self.history_client.last_error or 'HISTORY_QUERY_UNAVAILABLE_OR_INVALID')
        return out

    def discover_contracts(self,spot,now=None,option_type=None):
        """Use the indicative chain only to discover OCC IDs, never its prices."""
        now=now or datetime.now(timezone.utc)
        if not finite(spot) or spot<=0:raise ValueError('SPOT_REQUIRED_FOR_DISCOVERY')
        if option_type not in (None,'call','put'):raise ValueError('INVALID_DISCOVERY_TYPE')
        from core.sessions import ET
        day=now.astimezone(ET).date()
        result={'provider':'alpaca','discovery_feed':'INDICATIVE','fetched_at':now.isoformat(),
                'quality':'DATA_INCOMPLETE','contracts':[],'prices_discarded':True,
                'contract_terms_independently_verified':False,'live_ready':False}
        try:
            params={'feed':'indicative','limit':20,
                'expiration_date_gte':day.isoformat(),'expiration_date_lte':(day+timedelta(days=7)).isoformat(),
                'strike_price_gte':round(spot*.98,2),'strike_price_lte':round(spot*1.02,2)}
            if option_type:params['type']=option_type
            raw=self.history_client.get('/v1beta1/options/snapshots/SPY',params)
            snapshots=raw['snapshots']
            if not isinstance(snapshots,dict) or len(snapshots)>20:raise ValueError('INVALID_DISCOVERY_ROWS')
            specs=[]
            for symbol in snapshots:
                spec=contract(symbol)
                if not day.isoformat()<=spec['expiry']<=(day+timedelta(days=7)).isoformat():raise ValueError('INVALID_DISCOVERY_EXPIRY')
                if not spot*.98<=float(spec['strike'])<=spot*1.02:raise ValueError('INVALID_DISCOVERY_STRIKE')
                if option_type and spec['type']!=('C' if option_type=='call' else 'P'):raise ValueError('INVALID_DISCOVERY_TYPE')
                specs.append({'symbol':symbol,'expiry':spec['expiry'],'type':spec['type'],'strike':spec['strike']})
            result.update(quality='DATA_OK' if specs else 'DATA_INCOMPLETE',contracts=specs,
                pagination_complete=not bool(raw.get('next_page_token')),reason='IDENTITY_DISCOVERY_ONLY')
        except Exception:
            result['reason']=self.history_client.last_error or 'DISCOVERY_UNAVAILABLE_OR_INVALID'
        return result

def fresh_headlines(value,now=None):
    now=now or datetime.now(timezone.utc)
    result=dict(value or {'quality':'DATA_INCOMPLETE','articles':[],'reason':'NO_HEADLINE_QUERY_YET'})
    try:
        age=(now-stamp(result['fetched_at'])).total_seconds()
        result['query_age_seconds']=age
        if age<0:result['quality']='DATA_INVALID'
        elif age>600 and result.get('quality')=='DATA_OK':result['quality']='DATA_STALE'
    except (ValueError,KeyError,TypeError):result['quality']='DATA_INCOMPLETE'
    return result

def headline_status(value):
    value=fresh_headlines(value)
    lines=['PROVIDER HEADLINE CHECK\n'+value['quality']+'; articles: '+str(len(value.get('articles',[])))+
        '\nQuery time: '+str(value.get('fetched_at','UNAVAILABLE'))+
        '\nSPY-tagged headlines only. Delay UNVERIFIED. Complete macro/event coverage is not established.']
    for article in value.get('articles',[])[:3]:
        words=article['headline'].split()
        url=article['url'] if len(article['url'])<=300 else '(Source URL available on local dashboard)'
        lines.append(' '.join(words[:8])+('…' if len(words)>8 else '')+'\n'+article['created_at']+'\n'+url)
    return '\n\n'.join(lines)
