import sys,json,re
from pathlib import Path
from options.ledger import Ledger
ROOT=Path(__file__).resolve().parents[1]
def main(data=None):
    data=json.load(sys.stdin) if data is None else data
    tenant=data.get('tenant')
    if tenant is not None and not re.fullmatch(r'[a-f0-9]{24}',tenant):
        print('Invalid private storage identifier.');return
    folder=ROOT/'monitoring/users'/tenant if tenant else ROOT/'options'
    folder.mkdir(parents=True,exist_ok=True)
    ledger=Ledger(folder/'reported.sqlite')
    try:
        if data['command']=='option_positions':
            items=ledger.positions()
            print('SPY option reports (not broker verified):\n'+'\n'.join(f"{p['contract']}: {p['quantity']} contracts; remaining cost USD{p['cost_usd']}; realized USD{p['realized_usd']}" for p in items) if items else 'No SPY option reports recorded.')
            print('No live mark/P&L available. Expired contracts require exercise/expiry reconciliation; never assumed closed.');return
        parts=data['text'].split()
        if data['command']=='void':
            if len(parts)!=1:raise ValueError('Use /void EVENT_ID for your own private fill report')
            result=ledger.void(data['id'],parts[0])
            from core.storage import Store
            audit_store=Store(ROOT/'runtime/aegis.sqlite')
            try:audit_store.audit(data['id'],'user_fill_void',tenant or 'owner',{'target_event_id':parts[0],'result':result})
            finally:audit_store.close()
            print(result+'. Original event preserved. No order placed.');return
        force=bool(parts and parts[-1].upper()=='FORCE')
        if force:parts=parts[:-1]
        if len(parts)!=5:raise ValueError('Use /option_bought or /option_sold OCC_SYMBOL CONTRACTS PREMIUM TOTAL_FEES FILL_TIME_ISO_WITH_OFFSET')
        if tenant is None and data['command']=='option_bought' and not data.get('signal_id'):
            from core.storage import Store
            from data.models import stamp
            from datetime import datetime,timezone
            state=Store(ROOT/'runtime/aegis.sqlite')
            try:
                prompt=state.get('paper_fill_prompt:owner')
                if prompt and prompt['contract']==parts[0].upper() and stamp(prompt['expires_at'])>datetime.now(timezone.utc) and stamp(prompt['signal_timestamp'])<=stamp(parts[4])<=stamp(prompt['expires_at']):data['signal_id']=prompt['signal_id']
            finally:state.close()
        result=ledger.record(data['id'],'BUY' if data['command']=='option_bought' else 'SELL',parts[0].upper(),int(parts[1]),parts[2],parts[3],parts[4],force=force,signal_id=data.get('signal_id'))
        from core.storage import Store
        audit_store=Store(ROOT/'runtime/aegis.sqlite')
        try:audit_store.audit(data['id'],'user_fill_report',tenant or 'owner',{'contract':parts[0].upper(),'side':data['command'],'quantity':int(parts[1]),'result':result})
        finally:audit_store.close()
        print(result+'. Event ID: '+data['id']+'. Standard SPY contracts only, multiplier100; USD premium is per share. Report saved, no order placed. Option monitoring needs valid entitled quotes; no guaranteed exit coverage.')
    except (ValueError,KeyError,TypeError) as e:print('REPORT NOT RECORDED: '+str(e))
    finally:ledger.close()
if __name__=='__main__':main()
