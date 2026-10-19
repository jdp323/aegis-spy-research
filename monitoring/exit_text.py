"""Private exit review formatting; stale option data removes every option-dollar value."""
from core.signals import quote_valid,option_quote_valid

def format_review(contract,condition,plan,underlying,option,now):
    px=underlying.get('payload',{}).get('mid') if quote_valid(underlying,now) else None
    bid=option.get('payload',{}).get('bid') if option_quote_valid(option,now) else None
    targets=str(plan.get('t1','UNAVAILABLE'))+' / '+str(plan.get('t2','UNAVAILABLE'))
    premium='original estimated premiums '+str(plan.get('option_t1','UNAVAILABLE'))+' / '+str(plan.get('option_t2','UNAVAILABLE')) if bid is not None else 'option targets UNAVAILABLE — fresh option quote required'
    return 'EXIT REVIEW — '+contract+'\n'+condition+'\nSPY '+(f'{px:.2f}' if px is not None else 'UNAVAILABLE')+' / option bid '+(f'{bid:.2f}' if bid is not None else 'UNAVAILABLE — SPY levels only')+'\nTargets SPY '+targets+'; '+premium+'\nData: '+underlying.get('provider','UNAVAILABLE')+'; user-reported holding. Manual review only; no order placed.'
