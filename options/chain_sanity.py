"""Independent neighboring-strike checks. Missing real neighbors are a rejection."""
from core.signals import option_quote_valid
from data.models import finite

def verify(best,records,now):
    if not best:return ['NO_ELIGIBLE_OPTION_CONTRACT']
    peers=[c for c in records if c.get('type')==best.get('type') and c.get('expiry')==best.get('expiry') and option_quote_valid(c.get('quote',{}),now)]
    try:
        strike=float(best['strike']);peers=sorted(peers,key=lambda c:float(c['strike']))
        below=[c for c in peers if float(c['strike'])<strike];above=[c for c in peers if float(c['strike'])>strike]
        if not below or not above:return ['CHAIN_NEIGHBORS_UNAVAILABLE']
        triple=[below[-1],best,above[0]];strikes=[float(c['strike']) for c in triple]
        if any(not finite(k) or k<=0 for k in strikes) or not strikes[0]<strikes[1]<strikes[2]:return ['CHAIN_STRIKE_GRID_INVALID']
        if any(not finite(c.get('bid')) or not finite(c.get('ask')) or not 0<c['bid']<=c['ask'] for c in triple):return ['CHAIN_NEIGHBOR_PRICES_INVALID']
        # Crossed vertical spreads are impossible without a timing/liquidity discrepancy.
        if best['type']=='C':bad=any(a['ask']<b['bid'] for a,b in zip(triple,triple[1:]))
        else:bad=any(a['bid']>b['ask'] for a,b in zip(triple,triple[1:]))
        if bad:return ['CHAIN_NEIGHBOR_PRICE_INCONSISTENCY']
        return []
    except (ValueError,KeyError,TypeError):return ['CHAIN_STRUCTURE_UNAVAILABLE']
