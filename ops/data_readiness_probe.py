"""Bounded read-only market endpoint probes. No brokerage/account/order access."""
import json,os,sys,subprocess,time
from datetime import datetime,timezone
from core.storage import ROOT
from data.models import quote
from data.providers import AlpacaProvider
from data.reliability import quote_diagnostics

def probe():
    results=[]
    for feed,path,params in (
        ('IEX','/v2/stocks/SPY/quotes/latest',{'feed':'iex'}),
        ('SIP','/v2/stocks/SPY/quotes/latest',{'feed':'sip'}),
        ('OPRA','/v1beta1/options/snapshots/SPY',{'feed':'opra','limit':1})):
        provider=AlpacaProvider();start=time.monotonic();row={'feed':feed,'endpoint':path,'at':datetime.now(timezone.utc).isoformat()}
        try:
            raw=provider.get(path,params);received=datetime.now(timezone.utc).isoformat()
            row.update(status='MARKET_ENDPOINT_RESPONSE_RECEIVED',received_at=received)
            if feed!='OPRA':
                q=quote('alpaca-'+feed.lower(),'SPY',raw.get('quote',{}),received=received).view()
                row['quote_diagnostics']=quote_diagnostics(q,datetime.now(timezone.utc),'alpaca-'+feed.lower())
                row['source_timestamp']=q.get('source_timestamp');row['underlying_entry_fresh']=row['quote_diagnostics']['predicate'] is None
            else:
                snapshots=raw.get('snapshots') or {};row['returned_contracts']=len(snapshots)
                row['timestamped_quote_contracts']=sum(bool(v.get('latestQuote',{}).get('t')) for v in snapshots.values())
                row['timestamped_greek_contracts']=sum(bool(v.get('greeksTimestamp')) for v in snapshots.values())
                row['option_entry_eligible']=False;row['note']='Endpoint response alone never proves chain completeness, current executable quotes, liquidity or strategy eligibility.'
        except Exception as error:row.update(status='UNAVAILABLE',error_type=type(error).__name__,provider_error_class=provider.last_error)
        row['duration_seconds']=round(time.monotonic()-start,3);results.append(row)
    return {'at':datetime.now(timezone.utc).isoformat(),'scope':'Three authorized market-data requests; no account/balance/order requests. Closed-session observations cannot establish live readiness.','probes':results,'LIVE_SIGNAL_READY':False}

def main():
    # Keys stay inside the application's authorized child environment, never
    # command arguments, stdout, source manifests or the report.
    if '--authorized-child' not in sys.argv:
        from data.credentials import child_environment
        child=subprocess.run([sys.executable,'-X','utf8','-m','ops.data_readiness_probe','--authorized-child'],cwd=ROOT,env=child_environment(),capture_output=True,text=True,timeout=40)
        if child.returncode:raise RuntimeError('READINESS_PROBE_CHILD_FAILED')
        result=json.loads(child.stdout)
        folder=ROOT/'research/completion_verification';folder.mkdir(parents=True,exist_ok=True)
        p=folder/'MARKET_DATA_PROBE.json';p.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
    else:print(json.dumps(probe()))

if __name__=='__main__':main()
