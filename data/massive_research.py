"""Documented Massive aggregates adapter. Research only until delay is verified.

No keys in URLs, logs or returned health; no automatic subscription purchase.
Options and live quotes remain unavailable rather than synthesized from bars.
"""
import os,json,time,math,urllib.request,urllib.error
from datetime import datetime,timezone,timedelta
from urllib.parse import urlencode
from data.models import Datum,Quality,unavailable
from core.sessions import ET,market_session

BASE='https://api.massive.com'
SOURCE=BASE+'/v2/aggs/ticker/SPY/range/5/minute'
class MassiveResearchProvider:
    name='massive'
    def __init__(self,transport=None,now=None):
        self.transport=transport;self.now=now or (lambda:datetime.now(timezone.utc));self.retry_at=0;self.last_error=None;self.latency_ms=None
    def health(self):
        configured=bool(self.transport or os.getenv('MASSIVE_API_KEY'))
        return {'provider':self.name,'status':Quality.INCOMPLETE if configured else Quality.UNCONFIGURED,'entitlement':'DELAY_UNVERIFIED','scope':'UNDERLYING_BAR_RESEARCH_ONLY','last_error':self.last_error,'retry_after_seconds':max(0,self.retry_at-time.monotonic()),'request_latency_ms':self.latency_ms}
    def get(self,path,params):
        if self.health()['status']==Quality.UNCONFIGURED:raise ValueError('FEED_NOT_CONFIGURED')
        if time.monotonic()<self.retry_at:raise ValueError('RATE_LIMIT_COOLDOWN')
        started=time.monotonic()
        try:
            if self.transport:result=self.transport(path,params)
            else:
                request=urllib.request.Request(BASE+path+'?'+urlencode(params),headers={'Authorization':'Bearer '+os.environ['MASSIVE_API_KEY'],'User-Agent':'AEGIS-research/1.0'})
                with urllib.request.urlopen(request,timeout=15) as r:body=r.read(8_000_001)
                if len(body)>8_000_000:raise ValueError('RESPONSE_TOO_LARGE')
                result=json.loads(body)
            self.last_error=None;return result
        except urllib.error.HTTPError as e:
            self.last_error='HTTP_'+str(e.code)
            if e.code in (401,403,429):self.retry_at=time.monotonic()+(300 if e.code!=429 else 60)
            raise ValueError(self.last_error) from None
        finally:self.latency_ms=(time.monotonic()-started)*1000
    def get_bars(self,symbol='SPY',timeframe='5Min'):
        if symbol!='SPY' or timeframe!='5Min':return unavailable(self.name,symbol,'bars',Quality.INCOMPLETE,'UNSUPPORTED_RESEARCH_SCOPE')
        if self.health()['status']==Quality.UNCONFIGURED:return unavailable(self.name,symbol,'bars')
        now=self.now();end=now.astimezone(ET).date();start=end-timedelta(days=10)
        path='/v2/aggs/ticker/SPY/range/5/minute/'+start.isoformat()+'/'+end.isoformat()
        try:
            doc=self.get(path,{'adjusted':'false','sort':'asc','limit':50000})
            if doc.get('ticker')!='SPY' or doc.get('status') not in ('OK','DELAYED') or doc.get('adjusted') is not False or doc.get('next_url'):raise ValueError('INCOMPLETE_OR_INVALID_RESPONSE')
            bars=[]
            for r in doc.get('results',[]):
                if type(r.get('t')) is not int or r['t']%300000:raise ValueError('INVALID_BAR_TIMESTAMP')
                values=[r.get(k) for k in ('o','h','l','c','v')]
                if any(type(v) not in (int,float) or not math.isfinite(v) for v in values):raise ValueError('INVALID_BAR')
                o,h,l,c,v=values
                if not 0<l<=min(o,c)<=max(o,c)<=h or v<0:raise ValueError('INVALID_BAR')
                if r['t']/1000>now.timestamp():raise ValueError('FUTURE_BAR')
                bars.append({'timestamp':r['t']//1000,'open':o,'high':h,'low':l,'close':c,'volume':v})
            if not bars or any(a['timestamp']>=b['timestamp'] for a,b in zip(bars,bars[1:])):raise ValueError('EMPTY_OR_UNORDERED_BARS')
            return Datum(self.name,'SPY','bars',datetime.fromtimestamp(bars[-1]['timestamp'],timezone.utc).isoformat(),now.isoformat(),Quality.INCOMPLETE,'DELAY_UNVERIFIED',{'bars':bars,'timeframe':'5Min','source':SOURCE,'raw_response':doc,'complete':True},reason='Plan delay/entitlement not verified; research only')
        except Exception as e:
            reason=str(e) if isinstance(e,ValueError) and str(e) in ('HTTP_401','HTTP_403','HTTP_429','RATE_LIMIT_COOLDOWN','INCOMPLETE_OR_INVALID_RESPONSE','INVALID_BAR_TIMESTAMP','INVALID_BAR','FUTURE_BAR','EMPTY_OR_UNORDERED_BARS') else 'PROVIDER_OR_SCHEMA_UNAVAILABLE'
            return unavailable(self.name,symbol,'bars',Quality.DISCONNECTED,reason)
    def get_underlying_quote(self,symbol='SPY'):return unavailable(self.name,symbol,'quote',Quality.INCOMPLETE,'VERIFIED_QUOTE_ADAPTER_UNAVAILABLE')
    def get_option_quote(self,symbol):return unavailable(self.name,symbol,'quote',Quality.INCOMPLETE,'VERIFIED_OPTION_ADAPTER_UNAVAILABLE')
    def get_option_chain(self,symbol='SPY'):return unavailable(self.name,symbol,'chain',Quality.INCOMPLETE,'VERIFIED_OPTION_ADAPTER_UNAVAILABLE')
    def get_market_status(self):return market_session(self.now())
