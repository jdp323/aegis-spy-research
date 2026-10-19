"""Deterministic synthetic demonstration, isolated from real account state."""
import json
import tempfile
from pathlib import Path
from dataclasses import asdict, replace
from datetime import datetime, timezone, timedelta
from risk.v2 import RiskEngineV2, AccountSnapshot, CycleLedger, MarketQuote, MarketSession, StrategyEvidence, Proposal
from accounting.cycles import CycleLedger as ProfitLedger
from core.service import ROOT

def run_demo(output_root=ROOT):
    output_root=Path(output_root)
    (output_root/'research').mkdir(parents=True,exist_ok=True)
    (output_root/'monitoring/outbox').mkdir(parents=True,exist_ok=True)
    now=datetime.now(timezone.utc)
    stamp=now.timestamp()
    with tempfile.TemporaryDirectory(prefix='aegis-demo-') as folder:
        base=Path(folder)
        ledger=CycleLedger('DEMO-CYCLE',1,51,51,0,21,0,stamp,True)
        account=AccountSnapshot(51,51,51,0,0,0,0,{}, {},ledger,stamp,True,True)
        quote=MarketQuote('DEMO_ONLY',9.98,10,stamp)
        session=MarketSession('DEMO_ONLY',True,stamp,True)
        proposal=Proposal('DEMO-BUY','DEMO_ONLY','BUY',2,10,.20,True,3,1,
                          'Synthetic trend could reverse; gap losses can exceed the model.',
                          'DEMO-STRATEGY','SYNTHETIC-NOT-VALIDATION',stamp+120)
        engine=RiskEngineV2(base/'demo-risk.sqlite',{'DEMO-STRATEGY':StrategyEvidence('SYNTHETIC-NOT-VALIDATION',stamp,stamp+600,True)})
        buy=engine.evaluate(account,quote,session,proposal,now=stamp)
        duplicate=engine.evaluate(account,quote,session,replace(proposal,proposal_id='DEMO-DUPLICATE'),now=stamp)
        stale=engine.evaluate(account,replace(quote,timestamp=stamp-31),session,proposal,now=stamp)
        expired=engine.pending(now=stamp+121)[0]['review_status']
        engine.resolve('DEMO-BUY',status='OWNER_CANCELLED',owner_confirmation=True,
                       reason='SIMULATION ONLY: no order ever submitted',reconciled_account=account,now=stamp)
        sell_account=replace(account,own_cash_cad=30.8,equity_cad=52.8,peak_equity_cad=52.8,
                             holdings={'DEMO_ONLY':2},open_positions=1)
        sell_quote=MarketQuote('DEMO_ONLY',11,11.02,stamp)
        sell=engine.evaluate(sell_account,sell_quote,session,
            replace(proposal,proposal_id='DEMO-SELL',side='SELL',limit_price=11,expected_net_profit_cad=1.60),now=stamp)
        engine.close()
        profits=ProfitLedger(base/'demo-ledger.sqlite')
        profits.initialize('demo-init',starting_capital='51.00',verified=True)
        profits.open_cycle('demo-open','demo-cycle')
        profit=profits.close_cycle('demo-close','demo-cycle',terminal_equity='52.60',gross_realized_pnl='2.00',fees='0.40',reconciled=True,open_positions=0,open_orders=0)
    result={'demo':True,'generated_at':now.isoformat(),'disclaimer':'Invented symbol, prices, strategy, market session, evidence and fills. Not a recommendation or live account result.',
            'buy':asdict(buy),'duplicate':asdict(duplicate),'stale_quote':asdict(stale),
            'expiry':expired,'sell':asdict(sell),'profit_cycle':profit,
            'example_math':{'start_cad':51,'buy_shares':2,'buy_price_cad':10,'buy_fee_cad':.20,'cash_after_buy_cad':30.80,'sell_price_cad':11,'sell_fee_cad':.20,'ending_cash_cad':52.60,'net_profit_cad':1.60,'protected_cad':51,'next_stake_cad':1.60}}
    (output_root/'research/demo_result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    texts=[
      'DEMO ONLY — MARKET-OPEN MESSAGE EXAMPLE\nA real review would verify the exchange session and fresh data first.\nCurrent actual status: no actionable proposal; historical account snapshot and no validated strategy. No trade has been placed. Periodic reviews are not continuous exit monitoring.',
      'DEMO ONLY — INVENTED BUY-REVIEW CARD\nSymbol: DEMO_ONLY (fictional; do not search for or trade it).\nHypothetical limit: CAD10.00 × 2 shares. Assumed entry fee CAD0.20; cash required CAD20.20.\nIllustrative exit trigger CAD9.00; a stop is not guaranteed. Gap-stress loss CAD3.00 + entry fee CAD0.20; this is modeled, not a maximum possible loss.\nHypothetical target CAD11.00. Validity example: 2 minutes from a fresh verified quote.\nReason: synthetic trend example. Opposing case: reversal or adverse gap.\nThis passed a separate TEST gate using invented evidence, not the live strategy registry. No buy instruction or order.',
      'DEMO ONLY — EXIT / PROFIT MESSAGE EXAMPLE\nAssume both fictional shares sell at CAD11.00, with CAD0.20 exit fee.\nGross gain CAD2.00 minus CAD0.40 total fees = CAD1.60 net gain.\nStarting CAD51 → ending CAD52.60. After a reconciled flat profitable cycle: reserve CAD51; next stake CAD1.60. That tiny stake may support no feasible trade.\nAlso demonstrated: stale quote rejected; duplicate rejected; expired proposal flagged and reservation retained.\nActual account, cash, strategy registry and orders were not changed. Try /status, /news or /request in this chat.'
    ]
    events=[]
    for n,text in enumerate(texts,1):
        event={'id':f'demo-walkthrough-{now.strftime("%Y%m%dT%H%M%S")}-{n}','kind':'TEST','expires_at':(now+timedelta(minutes=30)).isoformat(),'text':text}
        file=output_root/'monitoring/outbox'/f'{event["id"]}.json'
        file.write_text(json.dumps(event,indent=2),encoding='utf-8');events.append(str(file))
    return {'result':result,'events':events}

if __name__=='__main__':print(json.dumps(run_demo(),indent=2))
