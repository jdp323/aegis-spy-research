"""Read-only market-data verification, never prints secrets or personal identifiers."""
import json
from datetime import datetime,timezone
from core.storage import ROOT
from data.questrade import QuestradeProvider
def check(provider=None):
    p=provider or QuestradeProvider();out={'at':datetime.now(timezone.utc).isoformat(),'health':p.health()}
    if out['health']['status']=='QUESTRADE_NOT_CONFIGURED':return out
    p.get_market_status();q=p.get_underlying_quote().view();chain=p.get_option_chain();structure=chain.payload.get('structure',[])
    out['underlying']={k:q.get(k) for k in ('provider','quality','entitlement','source_timestamp','freshness_seconds','reason')};out['underlying']['delay']=q.get('payload',{}).get('delay_indicator')
    if structure:
        s=structure[0]['symbol'];d=p.get_option_quote(s).view();raw=d.get('payload',{}).get('raw_greeks',{})
        out['option']={k:d.get(k) for k in ('symbol','quality','entitlement','source_timestamp','freshness_seconds','reason')};out['option']['delay']=d.get('payload',{}).get('delay_indicator');out['option']['greeks_present']=[k for k,v in raw.items() if v is not None]
    else:out['option']={'status':'UNAVAILABLE'}
    out['health']=p.health();return out
def main():
    d=check();path=ROOT/'daily_reports'/('QUESTRADE_CHECK_'+datetime.now(timezone.utc).date().isoformat()+'.md');path.parent.mkdir(exist_ok=True);path.write_text('# Read-only Questrade check\n\n```json\n'+json.dumps(d,indent=2)+'\n```\n\nNo order or personal account endpoint was accessed. Unknown quote timestamps stay unavailable.\n',encoding='utf-8');print(json.dumps({'report':str(path),**d}))
if __name__=='__main__':main()
