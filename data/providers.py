"""Provider boundary: explicit feed quality; no automatic quality downgrade."""
import os,json,time,re,urllib.request,urllib.error
from urllib.parse import urlencode
from datetime import datetime,timezone,timedelta
from typing import Protocol
from data.models import Datum,Quality,quote,unavailable
from core.sessions import market_session
class MarketDataProvider(Protocol):
    name:str
    def get_underlying_quote(self,symbol='SPY'):...
    def get_bars(self,symbol='SPY',timeframe='1Min'):...
    def get_option_chain(self,symbol='SPY'):...
    def get_option_quote(self,symbol):...
    def get_market_status(self):...
    def health(self):...
class UnconfiguredProvider:
    def __init__(self,name='secondary'):self.name=name
    def get_underlying_quote(self,symbol='SPY'):return unavailable(self.name,symbol,'quote')
    def get_bars(self,symbol='SPY',timeframe='1Min'):return unavailable(self.name,symbol,'bars')
    def get_option_chain(self,symbol='SPY'):return unavailable(self.name,symbol,'chain')
    def get_option_quote(self,symbol):return unavailable(self.name,symbol,'quote')
    def get_market_status(self):return market_session()
    def health(self):return {'provider':self.name,'status':Quality.UNCONFIGURED}
class AlpacaProvider(UnconfiguredProvider):
    def __init__(self,transport=None):
        super().__init__('alpaca');self.transport=transport;self.retry_at=0;self.last_error=None;self.latency_ms=None
    def health(self):return {'provider':self.name,'status':Quality.OK if self.transport or (os.getenv('APCA_API_KEY_ID') and os.getenv('APCA_API_SECRET_KEY')) else Quality.UNCONFIGURED,'entitlement':'UNVERIFIED_UNTIL_RESPONSE','last_error':self.last_error,'retry_after_seconds':max(0,self.retry_at-time.monotonic()),'request_latency_ms':self.latency_ms}
    def get(self,path,params):
        if not re.fullmatch(r'/v2/stocks/SPY/(?:quotes/latest|bars)|/v1beta1/options/(?:quotes/latest|snapshots/SPY|bars)|/v1beta1/news|/v1/corporate-actions',path):raise ValueError('MARKET_ENDPOINT_FORBIDDEN')
        if self.health()['status']==Quality.UNCONFIGURED:raise RuntimeError('FEED_NOT_CONFIGURED')
        if time.monotonic()<self.retry_at:raise RuntimeError('RATE_LIMIT_COOLDOWN')
        start=time.monotonic()
        try:
            if self.transport:return self.transport(path,params)
            req=urllib.request.Request('https://data.alpaca.markets'+path+'?'+urlencode(params),headers={'APCA-API-KEY-ID':os.getenv('APCA_API_KEY_ID'),'APCA-API-SECRET-KEY':os.getenv('APCA_API_SECRET_KEY')})
            with urllib.request.urlopen(req,timeout=10) as r:
                body=r.read(2*1024*1024+1)
                if len(body)>2*1024*1024:raise ValueError('PROVIDER_BODY_LIMIT')
                result=json.loads(body)
                if not isinstance(result,dict):raise ValueError('PROVIDER_RESPONSE_NOT_OBJECT')
            self.last_error=None;return result
        except urllib.error.HTTPError as e:
            self.last_error='HTTP_'+str(e.code)
            if e.code==429:
                try:delay=float(e.headers.get('Retry-After','60'))
                except (TypeError,ValueError):delay=60
                self.retry_at=time.monotonic()+max(60,min(900,delay))
            elif e.code in (401,403):self.retry_at=time.monotonic()+300
            raise RuntimeError(self.last_error) from None
        finally:self.latency_ms=(time.monotonic()-start)*1000
    def fail(self,symbol,kind):return unavailable(self.name,symbol,kind,Quality.UNCONFIGURED if self.health()['status']==Quality.UNCONFIGURED else Quality.DISCONNECTED,'Provider unavailable; no indicative fallback')
    def get_underlying_quote(self,symbol='SPY'):
        try:return quote('alpaca-sip',symbol,self.get('/v2/stocks/'+symbol+'/quotes/latest',{'feed':'sip'})['quote'])
        except Exception:return self.fail(symbol,'quote')
    def get_option_quote(self,symbol):
        from options.ledger import contract
        contract(symbol)
        try:return quote('alpaca-opra',symbol,self.get('/v1beta1/options/quotes/latest',{'symbols':symbol,'feed':'opra'})['quotes'][symbol])
        except Exception:return self.fail(symbol,'quote')
    def get_bars(self,symbol='SPY',timeframe='1Min'):
        try:
            rows=[];token=None
            for _ in range(10):
                params={'feed':'sip','timeframe':timeframe,'limit':10000,'adjustment':'raw','start':(datetime.now(timezone.utc)-timedelta(days=400 if timeframe=='1Day' else 14)).isoformat()}
                if token:params['page_token']=token
                r=self.get('/v2/stocks/'+symbol+'/bars',params);rows.extend(r.get('bars') or []);token=r.get('next_page_token')
                if not token:break
            return Datum(self.name,symbol,'bars',rows[-1]['t'] if rows else None,quality=Quality.INCOMPLETE if token or not rows else Quality.OK,entitlement='REALTIME',payload={'bars':rows,'timeframe':timeframe,'complete':not bool(token)})
        except Exception:return self.fail(symbol,'bars')
    def get_option_chain(self,symbol='SPY'):
        try:
            rows={};token=None
            for _ in range(10):
                params={'feed':'opra','limit':1000,'expiration_date_gte':market_session()['date'],'expiration_date_lte':(datetime.now(timezone.utc)+timedelta(days=30)).date().isoformat()}
                if token:params['page_token']=token
                r=self.get('/v1beta1/options/snapshots/'+symbol,params);rows.update(r.get('snapshots') or {});token=r.get('next_page_token')
                if not token:break
            # Each contract retains separate quote/Greek provenance; OI/volume are not invented.
            received=datetime.now(timezone.utc).isoformat()
            for raw in rows.values():raw['received_timestamp']=received;raw['feed_quality']='OPRA';raw['data_provider']='alpaca-opra'
            timestamps=[r.get('latestQuote',{}).get('t') for r in rows.values() if r.get('latestQuote',{}).get('t')]
            return Datum(self.name,symbol,'chain',min(timestamps) if timestamps else None,received,quality=Quality.INCOMPLETE if token or not rows else Quality.OK,entitlement='REALTIME',payload={'contracts':rows,'complete':not bool(token)})
        except Exception:return self.fail(symbol,'chain')
class PublicProvider(UnconfiguredProvider):
    def __init__(self):super().__init__('yahoo-public')
    def get_bars(self,symbol='SPY',timeframe='5Min'):
        if symbol!='SPY' or timeframe!='5Min':return unavailable(self.name,symbol,'bars',reason='UNSUPPORTED_TIMEFRAME')
        from core.storage import ROOT
        try:
            d=json.loads((ROOT/'research/public_spy_latest.json').read_text());return Datum(self.name,symbol,'bars',d.get('last_bar_at'),received_timestamp=d.get('fetched_at'),quality=Quality.INCOMPLETE,entitlement='DELAY_UNVERIFIED',payload=d,reason='Historical/public research only')
        except Exception:return unavailable(self.name,symbol,'bars',Quality.INCOMPLETE)
class ProviderRouter:
    def __init__(self,primary,secondary=None,public=None):self.providers=[primary,secondary or UnconfiguredProvider(),public or PublicProvider()]
    def request(self,method,*args,allow_research=False):
        attempts=[]
        for p in self.providers:
            d=getattr(p,method)(*args);v=d.view(max_age=120 if method=='get_bars' else 15);attempts.append({'provider':p.name,'quality':v['quality'],'entitlement':v['entitlement']})
            from core.isolation import assert_real
            try:assert_real(v)
            except ValueError:continue
            if v['quality']==Quality.OK and v['entitlement']=='REALTIME' and v.get('feed_quality',v.get('payload',{}).get('feed_quality')) not in ('INDICATIVE','DELAYED'):return v,attempts
            if allow_research and d.payload and p==self.providers[-1]:return v,attempts
        return {**v,'quality':Quality.INCOMPLETE,'reason':'NO_USABLE_REQUIRED_DATA','payload':{}},attempts
