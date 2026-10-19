"""Private review warnings and conservative bid marks; never executes an exit."""
from datetime import datetime,timezone
from options.ledger import contract
from core.sessions import ET,market_session
from data.models import stamp
def review(position,option_quote,underlying,plan=None,news=None,regime=None,now=None):
    now=now or datetime.now(timezone.utc);plan=plan or {};spec=contract(position['contract']);dte=(datetime.fromisoformat(spec['expiry']).date()-now.astimezone(ET).date()).days;alerts=[]
    result={**position,'dte':dte,'estimated_pnl_usd':None,'estimated_liquidation_usd':None,'alerts':alerts,'mark_basis':'bid less recorded entry cost; exit fees not included','plan':plan}
    from core.signals import option_quote_valid,quote_valid
    fresh=option_quote_valid(option_quote or {},now)
    underlying_fresh=quote_valid(underlying or {},now,15)
    result['monitoring_status']='PRICE_AND_OPTION_MARKS' if fresh and underlying_fresh else 'UNDERLYING_ONLY' if underlying_fresh else 'LIMITED_DATA'
    result['position_status']='USER_REPORTED_OPEN_NOT_BROKER_VERIFIED'
    if not underlying_fresh:alerts.append('MONITORING_UNAVAILABLE — underlying conditions not checked; no exit inferred')
    if not fresh:alerts.append('ABNORMAL_DATA — option mark unavailable')
    else:
        q=option_quote['payload'];result['estimated_liquidation_usd']=q['bid']*100*position['quantity'];result['estimated_pnl_usd']=result['estimated_liquidation_usd']-float(position['cost_usd']);result['quote_timestamp']=option_quote['source_timestamp']
        spread=(q['ask']-q['bid'])/q['mid']
        if spread>.12:alerts.extend(['OPTION_SPREAD_DETERIORATION','LIQUIDITY_DETERIORATION'])
        if plan.get('option_stop') is not None and q['bid']<=plan['option_stop']:alerts.append('OPTION_STOP_CONDITION')
        for target in ('t1','t2'):
            if plan.get('option_'+target) is not None and q['bid']>=plan['option_'+target]:alerts.append(target.upper()+'_REACHED')
    if underlying_fresh:
        px=underlying['payload']['mid'];sign=1 if spec['type']=='C' else -1
        stop_px=plan.get('invalidation_bar_close') if plan.get('stop_bar_minutes') else px
        if plan.get('invalidation') is not None and stop_px is not None and (stop_px-plan['invalidation'])*sign<=0:alerts.append('UNDERLYING_INVALIDATION')
        if plan.get('underlying_entry') is not None and (px-plan['underlying_entry'])*sign<0:alerts.append('ADVERSE_UNDERLYING_MOVEMENT')
        for k in ('t1','t2'):
            if plan.get(k) is not None and (px-plan[k])*sign>=0:alerts.append(k.upper()+'_REACHED')
    if news and news.get('risk')=='HIGH':alerts.append('MAJOR_NEWS_RISK')
    if plan.get('regime') and regime and plan['regime']!=regime:alerts.append('VOLATILITY_OR_REGIME_CHANGE')
    if plan.get('signal_expiry') and now>=stamp(plan['signal_expiry']):alerts.append('SIGNAL_EXPIRED_REVIEW_PLAN')
    if plan.get('max_hold_until') and now>=stamp(plan['max_hold_until']):alerts.append('MAX_HOLD_TIME_REACHED')
    if dte<0:alerts.append('EXPIRATION_PASSED_MANUAL_RECONCILIATION_REQUIRED')
    elif dte==0:
        alerts.extend(['EXPIRATION_APPROACHING','ZERO_DTE_TIME_DECAY'])
        local=now.astimezone(ET)
        if local.hour*60+local.minute>=market_session(now)['close_minute']-60:alerts.append('ZERO_DTE_FINAL_HOUR_REVIEW')
    elif dte==1:alerts.append('EXPIRATION_APPROACHING')
    return result
