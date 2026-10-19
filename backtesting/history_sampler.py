"""Small after-close trade-bar samples, not executable option backtests."""
import hashlib,json
from datetime import datetime,timezone,timedelta,time
from core.storage import ROOT
from core.sessions import ET,market_session
from data.providers import AlpacaProvider
from data.models import finite,stamp

def window(now):
    day=now.astimezone(ET).date()
    for offset in range(8):
        candidate=day-timedelta(days=offset)
        session=market_session(datetime.combine(candidate,time(12),ET))
        close=datetime.combine(candidate,time(session['close_minute']//60,session['close_minute']%60),ET)
        if session['active'] and close<=now-timedelta(minutes=20):
            return datetime.combine(candidate,time(9,30),ET),close
    return None

def collect(inputs,now=None,root=ROOT,quote_client=None):
    now=now or datetime.now(timezone.utc);w=window(now)
    report={'checked_at':now.isoformat(),'status':'UNAVAILABLE','history':[],
            'executable_quote_dataset':False,'strategy_validated':False,'live_ready':False}
    if not w:return {**report,'reason':'NO_CLOSED_SUPPORTED_SESSION'}
    report['session_date']=w[0].date().isoformat()
    folder=root/'research/option_history'/now.strftime('%Y%m%dT%H%M%S%fZ');folder.mkdir(parents=True,exist_ok=False)
    try:
        raw=(quote_client or AlpacaProvider()).get('/v2/stocks/SPY/quotes/latest',{'feed':'iex'})['quote']
        if not all(finite(raw.get(k)) for k in ('bp','ap')) or not 0<raw['bp']<=raw['ap']:raise ValueError('INVALID_DISCOVERY_REFERENCE')
        age=(now-stamp(raw['t'])).total_seconds()
        if not 0<=age<=7*86400:raise ValueError('INVALID_DISCOVERY_REFERENCE_TIMESTAMP')
        spot=(raw['bp']+raw['ap'])/2;report['discovery_reference_timestamp']=raw.get('t')
        for kind in ('call','put'):
            discovery=inputs.discover_contracts(spot,now,option_type=kind)
            candidates=sorted(discovery['contracts'],key=lambda r:abs(float(r['strike'])-spot))
            if not candidates:
                report['history'].append({'type':kind,'quality':'DATA_INCOMPLETE','bars':0,'reason':discovery['reason']});continue
            item=candidates[0];data=inputs.historical_option_bars(item['symbol'],*w,now)
            body=json.dumps(data,indent=2,allow_nan=False).encode();path=folder/(item['symbol']+'.json');path.write_bytes(body)
            report['history'].append({'symbol':item['symbol'],'type':kind,'quality':data['quality'],
                'bars':len(data['bars']),'reason':data['reason'],'pagination_complete':data['pagination_complete'],
                'file':path.relative_to(root).as_posix(),'sha256':hashlib.sha256(body).hexdigest()})
        good=all(r['quality']=='DATA_OK' for r in report['history']) and len(report['history'])==2
        report.update(status='TRADE_BAR_SAMPLES_COLLECTED' if good else 'PARTIAL_OR_UNAVAILABLE',
            reason='Samples selected after the outcome; no strategy or executable-fill validation claimed.')
    except Exception as error:
        report['reason']='RESEARCH_COLLECTION_FAILED_'+type(error).__name__
    (folder/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report
