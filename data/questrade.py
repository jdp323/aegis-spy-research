"""Read-only Questrade market-data client; strict endpoint and TLS-origin allowlists."""
import json,re,time,random,urllib.request,urllib.error
from urllib.parse import urlencode,urlsplit
from datetime import datetime,timezone,timedelta
from data.models import Datum,Quality,finite,stamp,unavailable
from data.questrade_vault import Vault,locked
from core.sessions import market_session
ALLOWED=re.compile(r'^/(?:time|symbols(?:/search|/\d+(?:/options)?)?|markets/(?:candles/\d+|quotes(?:/\d+|/options)?))$')
def origin(value):
    u=urlsplit(value)
    if u.scheme!='https' or not re.fullmatch(r'api\d+\.iq\.questrade\.com',u.hostname or '') or u.username or u.password or u.port not in (None,443) or u.query or u.fragment or u.path not in ('','/','/v1','/v1/'):raise ValueError('UNVERIFIED_API_ORIGIN')
    return 'https://'+u.hostname
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise RuntimeError('REDIRECT_REJECTED')
def transport(url,method,headers,body=None):
    req=urllib.request.Request(url,data=body,headers=headers,method=method)
    with urllib.request.build_opener(NoRedirect()).open(req,timeout=8) as r:
        raw=r.read(2*1024*1024+1)
        if len(raw)>2*1024*1024:raise ValueError('PROVIDER_BODY_LIMIT')
        d=json.loads(raw)
        if not isinstance(d,dict):raise ValueError('PROVIDER_RESPONSE_NOT_OBJECT')
        return d
class QuestradeProvider:
    name='questrade'
    def __init__(self,vault=None,request=transport,config=None,clock=None,sleep=time.sleep,readonly=False):
        self.readonly=readonly;self.local_last_request=0;self.vault=vault or Vault();self.request=request;self.config=config or {};self.clock=clock or (lambda:datetime.now(timezone.utc));self.sleep=sleep;self.symbols={};self.chain_ids={};self.retry_at=0;self.failures=0;self.last_error=None;self.server_offset=None
    def session(self):
        now=self.clock()
        if self.readonly:
            d=self.vault.load()
            if not d:raise RuntimeError('QUESTRADE_NOT_CONFIGURED')
            if stamp(d['refresh_policy_deadline'])<=now or d.get('refresh_in_progress') or not d.get('access_token') or stamp(d['access_expires_at'])<=now+timedelta(seconds=30):raise RuntimeError('READONLY_CHECK_NEEDS_OWNER_REFRESH')
            return d
        with locked(self.vault.path):
            d=self.vault.load()
            if not d:raise RuntimeError('QUESTRADE_NOT_CONFIGURED')
            if d.get('refresh_in_progress'):raise RuntimeError('QUESTRADE_REFRESH_UNCERTAIN')
            if stamp(d['refresh_policy_deadline'])<=now:raise RuntimeError('QUESTRADE_TOKEN_EXPIRED')
            if d.get('access_token') and stamp(d['access_expires_at'])>now+timedelta(seconds=30) and (now-stamp(d['token_refreshed_at'])).total_seconds()<self.config.get('keep_alive_hours',12)*3600:return d
            d['refresh_in_progress']=True;self.vault.save(d)
            try:
                result=self.request('https://login.questrade.com/oauth2/token','POST',{'Content-Type':'application/x-www-form-urlencoded'},urlencode({'grant_type':'refresh_token','refresh_token':d['refresh_token']}).encode())
                if not all(isinstance(result.get(k),str) and result[k] for k in ('refresh_token','access_token','api_server')) or type(result.get('expires_in')) is not int or not 0<result['expires_in']<=86400 or result.get('token_type','Bearer').lower()!='bearer':raise ValueError('INVALID_REFRESH_RESPONSE')
                server=origin(result['api_server']);refreshed=self.clock()
                new={'entered_at':d['entered_at'],'refresh_token':result['refresh_token'],'access_token':result['access_token'],'api_server':server,'access_expires_at':(refreshed+timedelta(seconds=result['expires_in'])).isoformat(),'token_refreshed_at':refreshed.isoformat(),'refresh_policy_deadline':(refreshed+timedelta(hours=self.config.get('conservative_refresh_lifetime_hours',72))).isoformat(),'refresh_in_progress':False}
                self.vault.save(new) # Atomic encrypted persistence BEFORE returning access token.
                return new
            except Exception:
                # Unknown remote consumption: keep journal marked uncertain; never blind retry.
                raise RuntimeError('QUESTRADE_REFRESH_UNCERTAIN') from None
    def limit(self):
        """Shared market-request window, no token or personal identifiers in limiter file."""
        if self.readonly:
            delay=max(0,.25-(time.monotonic()-self.local_last_request))
            if delay:self.sleep(delay)
            self.local_last_request=time.monotonic();return
        p=self.vault.path.with_suffix('.rate.json');cap=self.config.get('request_cap_per_second',5)
        while True:
            with locked(p):
                now=self.clock().timestamp()
                try:rows=json.loads(p.read_text())
                except FileNotFoundError:rows=[]
                rows=[t for t in rows if 0<=now-t<3600]
                last=[t for t in rows if now-t<1]
                delay=max(0,1-(now-min(last))) if len(last)>=cap else max(0,3600-(now-min(rows))) if len(rows)>=14000 else 0
                if not delay:
                    tmp=p.with_suffix('.pending');tmp.write_text(json.dumps(rows+[now]));tmp.replace(p);return
            self.sleep(max(.01,delay))
    def get(self,path,params=None,method='GET',body=None):
        if not ALLOWED.fullmatch(path) or method not in ('GET','POST') or (method=='POST' and path!='/markets/quotes/options'):raise ValueError('ENDPOINT_FORBIDDEN')
        if time.monotonic()<self.retry_at:raise RuntimeError('QUESTRADE_COOLDOWN')
        d=self.session();self.limit()
        try:
            url=origin(d['api_server'])+'/v1'+path+('?' +urlencode(params) if params else '')
            result=self.request(url,method,{'Authorization':'Bearer '+d['access_token'],'Content-Type':'application/json'},json.dumps(body).encode() if body is not None else None);self.last_error=None;self.failures=0;return result
        except urllib.error.HTTPError as e:
            self.last_error='HTTP_'+str(e.code);self.failures+=1
            delay=300 if e.code in (401,403) else min(300,2**min(self.failures,8)+random.uniform(0,2))
            if e.code==429:
                try:delay=max(delay,min(900,float(e.headers.get('X-RateLimit-Reset',0))-self.clock().timestamp()))
                except (TypeError,ValueError):pass
            self.retry_at=time.monotonic()+max(1,delay)
            raise RuntimeError(self.last_error) from None
    def health(self):
        try:d=self.vault.status(self.clock())
        except Exception:d={'provider':self.name,'status':'QUESTRADE_VAULT_UNREADABLE'}
        return {**d,'entitlement':'UNVERIFIED_UNTIL_TIMESTAMPED_RESPONSE','server_offset_seconds':self.server_offset,'last_error':self.last_error,'retry_after_seconds':max(0,self.retry_at-time.monotonic())}
    def id(self,symbol):
        if symbol in self.symbols:return self.symbols[symbol]
        if symbol!='SPY':raise ValueError('SPY_ONLY')
        rows=self.get('/symbols/search',{'prefix':'SPY'}).get('symbols',[])
        matches=[r for r in rows if r.get('symbol')=='SPY' and r.get('listingExchange') in ('NYSE','NYSEARCA','NYSE Arca') and type(r.get('symbolId')) is int]
        if len(matches)!=1:raise ValueError('SPY_SYMBOL_NOT_UNAMBIGUOUS')
        self.symbols[symbol]=matches[0]['symbolId'];return matches[0]['symbolId']
    def parse_quote(self,symbol,row,options=False):
        """lastTradeTime is retained as trade metadata, NEVER used as bid/ask quote time."""
        delay=row.get('delay');realtime=type(delay) in (int,float) and delay==0 if options else delay is False
        quality=Quality.INCOMPLETE if realtime else Quality.STALE if delay is not None else Quality.INCOMPLETE
        bid,ask=row.get('bidPrice'),row.get('askPrice');valid=finite(bid) and finite(ask) and 0<bid<=ask
        if not valid:quality=Quality.INVALID
        payload={'bid':bid if finite(bid) else None,'ask':ask if finite(ask) else None,'mid':(bid+ask)/2 if valid else None,'delay_indicator':delay,'last_trade_timestamp':row.get('lastTradeTime'),'volume':row.get('volume'),'oi':row.get('openInterest'),'raw_greeks':{k:row.get(k) for k in ('delta','gamma','theta','vega','volatility')},'quote_timestamp_status':'UNAVAILABLE: official schema has no bid/ask source timestamp'}
        d=Datum('questrade',symbol,'quote',None,self.clock().isoformat(),quality,'UNVERIFIED',payload)
        # A later documented timestamp adapter may promote this. Current API evidence cannot.
        d.reason='QUOTE_SOURCE_TIMESTAMP_UNVERIFIED';return d
    def fail(self,symbol,kind):
        return unavailable(self.name,symbol,kind,Quality.UNCONFIGURED if self.health()['status']=='QUESTRADE_NOT_CONFIGURED' else Quality.INCOMPLETE,'Questrade unavailable or freshness unverified')
    def get_underlying_quote(self,symbol='SPY'):
        try:return self.parse_quote(symbol,self.get('/markets/quotes/'+str(self.id(symbol)))['quotes'][0])
        except Exception:return self.fail(symbol,'quote')
    def get_bars(self,symbol='SPY',timeframe='1Min'):
        if timeframe not in ('1Min','1Day'):return self.fail(symbol,'bars')
        try:
            now=self.clock();rows=self.get('/markets/candles/'+str(self.id(symbol)),{'startTime':(now-timedelta(days=7 if timeframe=='1Min' else 400)).isoformat(),'endTime':now.isoformat(),'interval':'OneMinute' if timeframe=='1Min' else 'OneDay'})['candles']
            out=[]
            for r in rows:
                if not all(finite(r.get(k)) for k in ('open','high','low','close','volume')) or stamp(r['end'])>now:continue
                out.append({'t':stamp(r['start']).astimezone(timezone.utc).isoformat(),'o':r['open'],'h':r['high'],'l':r['low'],'c':r['close'],'v':r['volume']})
            return Datum(self.name,symbol,'bars',out[-1]['t'] if out else None,now.isoformat(),Quality.OK if out else Quality.INCOMPLETE,'HISTORICAL',{'bars':out,'feed_quality':'QUESTRADE_CANDLES_UNVERIFIED_DELAY'})
        except Exception:return self.fail(symbol,'bars')
    def get_option_chain(self,symbol='SPY'):
        try:
            now=self.clock();rows=self.get('/symbols/'+str(self.id(symbol))+'/options').get('options',[]);structure=[]
            for expiry in rows:
                date=stamp(expiry['expiryDate']).date()
                for root in expiry.get('chainPerRoot',[]):
                    if root.get('root')!='SPY' or root.get('multiplier')!=100:continue
                    for r in root.get('chainPerStrikePrice',[]):
                        strike=r.get('strikePrice')
                        if not finite(strike) or strike<=0 or abs(strike*1000-round(strike*1000))>1e-6:continue
                        for kind,key in (('C','callSymbolId'),('P','putSymbolId')):
                            if type(r.get(key)) is not int:continue
                            occ='SPY'+date.strftime('%y%m%d')+kind+f'{round(strike*1000):08d}';self.chain_ids[occ]=r[key];structure.append({'symbol':occ,'symbol_id':r[key],'strike':strike,'type':kind,'expiry':date.isoformat(),'multiplier':100})
            return Datum(self.name,symbol,'chain',now.isoformat(),now.isoformat(),Quality.INCOMPLETE,'STRUCTURE_ONLY',{'contracts':{},'structure':structure,'feed_quality':'STRUCTURE_ONLY'},reason='Real option quotes and timestamp verification unavailable')
        except Exception:return self.fail(symbol,'chain')
    def get_option_quote(self,symbol):
        from options.ledger import contract
        contract(symbol)
        try:
            if symbol not in self.chain_ids:self.get_option_chain()
            sid=self.chain_ids[symbol];result=self.get('/markets/quotes/options',method='POST',body={'optionIds':[sid]});rows=result.get('optionQuotes',result.get('quotes',[]))
            matches=[r for r in rows if r.get('symbolId')==sid]
            if len(matches)!=1:raise ValueError('QUOTE_ID_MISMATCH')
            return self.parse_quote(symbol,matches[0],True)
        except Exception:return self.fail(symbol,'quote')
    def get_market_status(self):
        try:
            start=self.clock();t=stamp(self.get('/time')['time']);end=self.clock();self.server_offset=(t-(start+(end-start)/2)).total_seconds()
        except Exception:self.server_offset=None
        return market_session(self.clock())
    def keep_alive(self):
        h=self.health()
        if h['status'] not in ('QUESTRADE_NOT_CONFIGURED','QUESTRADE_REFRESH_UNCERTAIN','QUESTRADE_TOKEN_EXPIRED') and (h.get('token_refreshed_at') is None or h.get('token_age_hours',0)>=self.config.get('keep_alive_hours',12)):
            try:self.session()
            except RuntimeError:pass
        return self.health()
