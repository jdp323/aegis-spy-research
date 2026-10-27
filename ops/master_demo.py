"""Production renderers and notifier, fictional inputs and fake transport ONLY."""
import argparse,json,subprocess,sys,tempfile
from pathlib import Path
from datetime import datetime,timedelta,timezone
from core.sessions import ET
from core.storage import ROOT
from core.runtime_paths import node_executable
from data.models import quote
from ops.day_simulation import run_scenario
from monitoring.owner_messages import premarket_text,status_text,idea_text,update_text,recap_text

def gallery():
    now=datetime(2026,10,21,11,tzinfo=ET);bars=[dict(timestamp=now.timestamp()-(31-n)*60,open=500.,high=501.,low=499.,close=500.+n*.01,volume=100.) for n in range(31)]
    q=quote('alpaca-iex','SPY',{'bp':500.29,'ap':500.31,'t':now.isoformat()},received=now.isoformat()).view(now)
    ctx={'quote':q,'feed_quality':'IEX','reason':None,'bar_research':{'quality':'COMPLETED_BAR_RESEARCH_ONLY','reason':None,'bars':bars,'features':{'1m':{'vwap_approx':500.,'atr14':.2}},'feed_quality':'IEX'}}
    morning=now.replace(hour=9,minute=15);news={'quality':'DATA_OK','risk':'NORMAL','events':[]}
    report={'quality':'IEX_RESEARCH_ONLY','bias':'UP','as_of_bar':morning.replace(minute=10).isoformat(),'levels':{'last':500.3,'high':501.,'low':499.}}
    i={'signal_id':'a'*24,'strategy_version':'FIXTURE_ONLY','timestamp':now.isoformat(),'confirmation_at':now.isoformat(),'direction':'CALL','entry_mode':'ENTER NOW','entry_condition':'a completed 1-minute close above SPY $500.10','horizon_id':'H60','planned_holding_minutes':60,'trigger':500.1,'trigger_level':500.1,'reference_midpoint':500.3,'modeled_entry_fill':500.32,'actual_reported_fill':None,'entry':500.3,'do_not_chase':500.8,'invalidation':499.8,'t1':501.,'t2':501.3,'signal_expiry':(now+timedelta(minutes=1)).isoformat(),'max_hold_until':(now+timedelta(minutes=60)).isoformat(),'status':'OPEN','alerted':True,'opened_at':now.isoformat()}
    messages=[('PREOPEN',premarket_text(report,news,morning)),('TREND_LINE',status_text(ctx,now,news)),('SPY_IDEA',idea_text(i,{},{})),('IDEA_UPDATE',update_text(i,'STOP_HIT'))]
    out=dict(ctx,reason='quote age exceeded five seconds');messages.append(('TREND_LINE',status_text(out,now,news,plan=i)))
    messages.append(('RECAP',recap_text([dict(i,status='CLOSED')],now.replace(hour=16,minute=15),'UNAVAILABLE')))
    # An independently labelled schema fixture exercises the actual reference
    # verifier; it is never inserted into a market/option/fill store.
    c={'symbol':'SPY261023C00500000','type':'C','strike':500.,'expiry':'2026-10-23','bid':1.9,'ask':2.,'mid':1.95,'volume':1000,'oi':1000,'delta':.5,'gamma':.01,'theta':-.1,'vega':.1,'iv':.2,'greeks_timestamp':now.isoformat()}
    c['quote']=quote('alpaca-opra',c['symbol'],{'bp':1.9,'ap':2.,'t':now.isoformat()},received=now.isoformat()).view(now)
    from options.research_contract import verified_plan
    plan=verified_plan(i,{'best_contract':c,'chain_sanity_reasons':[]},now,{'options_risk':{'max_trade_premium_usd':500}})
    oi=dict(i,signal_id='b'*24,option_contract=c,option_plan=plan,option_verification='FRESH_QUOTE_GREEKS_CHAIN_SANITY_PASSED')
    messages.append(('SPY_IDEA',idea_text(oi,{},{})))
    caps={'PREOPEN':8,'TREND_LINE':7,'SPY_IDEA':12,'IDEA_UPDATE':5,'RECAP':8}
    for typ,text in messages:
        assert len(text.splitlines())<=caps[typ] and len(text)<=3500
        assert 'None' not in text and "{'" not in text
    return messages

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);a=p.parse_args();destination=Path(a.output)
    scenarios=[run_scenario('normal',datetime(2026,10,21).date(),restart=True),run_scenario('stale',datetime(2026,10,21).date())]
    with tempfile.TemporaryDirectory(prefix='ag-master-demo-') as directory:
        r=subprocess.run([node_executable(),'ops/schedule_transport.cjs'],cwd=ROOT,input=json.dumps({'scenarios':scenarios,'directory':directory}),capture_output=True,text=True,encoding='utf-8',timeout=60)
    transport=json.loads(r.stdout)
    if r.returncode or transport.get('status')!='PASS':raise ValueError('FAKE_TRANSPORT_FAILED')
    lines=['# AEGIS production-renderer demonstration','','Every price, quote, event, contract and outcome below is a FICTIONAL FIXTURE. This is software behavior, not actual market evidence, a live contract or a personal fill. No Telegram network, vault or guest was used.','','Actual notifier fake-transport result: '+json.dumps(transport),'','## Format fixtures','']
    for n,(typ,text) in enumerate(gallery(),1):lines+=['### Fixture '+str(n)+' · '+typ,'','```text',text,'```','']
    for scenario in scenarios:
        lines+=['## Full-day '+scenario['name']+' · synthetic / memory-only','',json.dumps(scenario['message_counts']),'']
        for e in scenario['timeline']:lines+=['### '+e['at_et']+' · '+e['alert_type']+(' · SILENT' if e['disable_notification'] else ''),'','```text',e['text'],'```','']
    with destination.open('x',encoding='utf-8',newline='\n') as f:f.write('\n'.join(lines))
    print(json.dumps({'status':'PASS','transport':transport,'scenarios':len(scenarios),'gallery':len(gallery()),'path':destination.name}))
if __name__=='__main__':main()
