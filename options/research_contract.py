"""Verified contract quote reference, independent of Greek price approximations."""
from datetime import datetime
from core.signals import option_quote_valid,quote_valid
from core.sessions import ET
from data.models import stamp,finite
from options.trade_plan import sanity

def current_reference(idea,now,config=None):
    """Same strict quote-reference check for view, renderer and publication."""
    from options.ledger import contract as parse
    c=idea.get('option_contract') or {};p=idea.get('option_plan') or {}
    try:
        term=parse(c['symbol']);end=stamp(idea['max_hold_until'])
        if idea.get('option_verification')!='FRESH_QUOTE_GREEKS_CHAIN_SANITY_PASSED' or not option_quote_valid(c['quote'],now) or not quote_valid(c['quote'],now,5):return None
        if sanity(c,now,config or {}):return None
        if not finite(c.get('oi')) or c['oi']<100 or not finite(c.get('volume')) or c['volume']<100:return None
        if c.get('bid')!=c['quote']['payload']['bid'] or c.get('ask')!=c['quote']['payload']['ask']:return None
        if datetime.fromisoformat(term['expiry']).date()<=end.astimezone(ET).date():return None
        if c.get('type')!=('C' if idea['direction']=='CALL' else 'P'):return None
        if not c.get('greeks_timestamp') or not 0<=(now-stamp(c['greeks_timestamp'])).total_seconds()<=60:return None
        if not finite(p.get('limit')) or p['limit']!=c['ask'] or p.get('eligible') is False:return None
        return c,p
    except (ValueError,KeyError,TypeError):return None

def verified_plan(idea,selection,now,config):
    c=selection.get('best_contract')
    if not c or selection.get('chain_sanity_reasons')!=[]:raise ValueError('VERIFIED_CHAIN_REQUIRED')
    if c.get('type')!=('C' if idea['direction']=='CALL' else 'P'):raise ValueError('CONTRACT_RIGHT_MISMATCH')
    if sanity(c,now,config) or not option_quote_valid(c.get('quote',{}),now) or not quote_valid(c.get('quote',{}),now,5):raise ValueError('FRESH_VERIFIED_BBO_REQUIRED')
    if not c.get('greeks_timestamp') or not 0<=(now-stamp(c['greeks_timestamp'])).total_seconds()<=60:raise ValueError('CURRENT_GREEKS_REQUIRED')
    if not finite(c.get('volume')) or c['volume']<100 or not finite(c.get('oi')) or c['oi']<100:raise ValueError('VERIFIED_LIQUIDITY_REQUIRED')
    if datetime.fromisoformat(c['expiry']).date()<=stamp(idea['max_hold_until']).astimezone(ET).date():raise ValueError('EXPIRY_BEYOND_HOLD_REQUIRED')
    if c['quote'].get('payload',{}).get('bid')!=c['bid'] or c['quote'].get('payload',{}).get('ask')!=c['ask']:raise ValueError('CONTRACT_BBO_FIELDS_MISMATCH')
    limit=c['ask'];fee=float(config.get('paper_fee_per_contract',.65));cost=round(limit*100+fee,2)
    if cost>config.get('options_risk',{}).get('max_trade_premium_usd',500):raise ValueError('PAPER_PREMIUM_BUDGET_EXCEEDED')
    return {'version':'verified-bbo-reference-v1','limit':limit,'cost':cost,'multiplier':100,'premium_at_risk':round(limit*100,2),'max_hold_until':idea['max_hold_until'],'eligible':True,'qualification':'CONTRACT_DATA_ONLY_NOT_STRATEGY_VALIDATION','fill_assumed':False,'option_profitability':'UNAVAILABLE','loss_at_stop':None,'limitations':'Ask-side quote reference; limit fills and personal orders are never assumed. Underlying stop does not cap option loss.'}
