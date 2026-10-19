"""Additive product/provider defaults, keeping unsupported live permissions false."""
import math
def number(v,low,high):return type(v) in (int,float) and math.isfinite(v) and low<=v<=high
def validate_new(c):
    if type(c.get('require_chain_sanity',True)) is not bool:raise ValueError('INVALID_CHAIN_SANITY_FLAG')
    if not number(c.get('max_future_skew_seconds',2),0,5):raise ValueError('INVALID_SKEW_BUDGET')
    if c.get('option_data_provider','questrade') not in ('questrade','alpaca'):raise ValueError('INVALID_OPTIONS_PROVIDER')
    q=c.get('questrade',{})
    for key,default,low,high in [('keep_alive_hours',12,1,24),('request_cap_per_second',5,1,5),('token_warning_hours',24,1,48),('conservative_refresh_lifetime_hours',72,24,168),('active_quote_seconds',10,5,60)]:
        if not number(q.get(key,default),low,high):raise ValueError('INVALID_QUESTRADE_POLICY')
    for key,defaults in [('price_mismatch_tolerance',{'percent':.1,'usd':.5}),('buy_limit_buffer',{'percent':4.,'usd':.1})]:
        for field,default in defaults.items():
            if not number(c.get(key,{}).get(field,default),0,5 if field=='percent' else 2):raise ValueError('INVALID_PRICE_POLICY')
    n=c.get('notifications',{})
    if n.get('profile','simple') not in ('simple','detailed'):raise ValueError('INVALID_NOTIFICATION_PROFILE')
    if any(k not in ('ideas','idea_updates','morning','system','periodic','changes','extended','news','sentiment','trend_lines') or type(v) is not bool for k,v in n.get('categories',{}).items()):raise ValueError('INVALID_NOTIFICATION_CATEGORY')
    h=c.get('horizons',{})
    if not number(h.get('scalp_minutes',60),1,60) or not number(h.get('intraday_exit_minutes_before_close',30),5,60) or not number(h.get('swing_days',3),2,7) or type(h.get('swing_enabled',False)) is not bool:raise ValueError('INVALID_HORIZON_POLICY')
    return c
