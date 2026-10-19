"""Read-only readiness report; no data fees, orders or credential output."""
import json
from datetime import datetime,timezone
from core.service import ROOT
from data.spy_feed import fetch_quotes
from options.ledger import Ledger
from core.upgrade_service import snapshot
from data.credentials import configured

def protected_probe_status(quotes,configuration):
    # This standalone process deliberately never decrypts the worker/stream vault.
    if quotes.get('status')=='FEED_NOT_CONFIGURED' and configuration['encrypted_config_present']:
        return {'status':'DATA_INCOMPLETE','action':'NO TRADE','quotes':{},
                'note':'Encrypted configuration exists; standalone quote probe has no process credentials. Use supervised stream health and fresh quote checks; configuration alone is not live readiness.'}
    return quotes

def run():
    path=ROOT/'options/reported.sqlite'
    positions=[]
    if path.exists():
        ledger=Ledger(path)
        try:positions=ledger.positions()
        finally:ledger.close()
    configuration=configured()
    quotes=protected_probe_status(fetch_quotes([p['contract'] for p in positions if p['quantity']>0]),configuration)
    current=snapshot()
    worker=current.get('worker_health') or {}
    provider=current.get('provider') or {}
    result={'checked_at':datetime.now(timezone.utc).isoformat(),'underlying':'SPY','mode':'RESEARCH_AND_MANUAL_REPORTS','option_ledger':'IMPLEMENTED_UNIT_TESTED','data':quotes,'continuous_monitor':'IMPLEMENTED_NOT_LIVE_READY','worker_state':worker.get('state','UNAVAILABLE'),'feed_status':provider.get('status','FEED_NOT_CONFIGURED'),'streams':current.get('streams'),'automatic_research':current.get('research_notification_health'),'validated_option_strategy':False,'live_signal_ready':False,'action':'NO TRADE','order_execution':False}
    result['credentials']=configuration
    result['provider_configuration_status']=result['feed_status']
    # DATA_OK from provider.health historically indicates configured process credentials.
    # It must not be presented as verified required-data quality.
    if result['feed_status']=='DATA_OK':result['feed_status']=(current.get('underlying') or {}).get('quality','DATA_INCOMPLETE')
    (ROOT/'research/monday_preflight.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
if __name__=='__main__':print(json.dumps(run(),indent=2))
