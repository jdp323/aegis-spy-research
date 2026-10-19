"""Independent options policy; no reuse of the historical CAD equity policy."""
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import math
def parse_limits(config):
    """Parse the four USD limits without supplying reconciliation or live authority."""
    result={}
    for key in ('max_trade_premium_usd','max_exposure_usd','max_daily_loss_usd','max_consecutive_losses'):
        v=config.get(key)
        if type(v) not in (int,float) or not math.isfinite(v) or v<=0:raise ValueError('UNCONFIGURED_'+key.upper())
        if key=='max_consecutive_losses' and type(v) is not int:raise ValueError('LOSS_LIMIT_MUST_BE_INTEGER')
        result[key]=v
    return result
def check(config,positions,premium=None,now=None,*,mode='live',live_confirmed=False):
    if mode not in ('paper','live'):raise ValueError('INVALID_RISK_MODE')
    if type(live_confirmed) is not bool:raise ValueError('INVALID_LIVE_CONFIRMATION')
    reasons=[];exposure=0
    try:
        for p in positions:
            quantity=p['quantity'];cost=float(p['cost_usd'])
            if type(quantity) is not int or quantity<0 or not math.isfinite(cost) or cost<0:raise ValueError()
            if quantity>0:exposure+=cost
    except (ValueError,KeyError,TypeError):reasons.append('INVALID_EXPOSURE_RECORD')
    for key in ('max_trade_premium_usd','max_exposure_usd','max_daily_loss_usd','max_consecutive_losses'):
        v=config.get(key)
        if type(v) not in (int,float) or not math.isfinite(v) or v<=0:reasons.append('UNCONFIGURED_'+key.upper())
    # A dated reconciliation marker is not evidence of zero loss or zero streak.
    daily_loss=config.get('daily_loss_usd');streak=config.get('consecutive_losses')
    if type(daily_loss) not in (int,float) or not math.isfinite(daily_loss) or daily_loss<0:reasons.append('INVALID_DAILY_LOSS_USD')
    if type(streak) is not int or streak<0:reasons.append('INVALID_CONSECUTIVE_LOSSES')
    clock=datetime.now(timezone.utc) if now is None else now
    if not isinstance(clock,datetime) or clock.tzinfo is None or clock.utcoffset() is None:reasons.append('INVALID_RISK_CLOCK')
    if type(config.get('max_consecutive_losses')) is not int:reasons.append('LOSS_LIMIT_MUST_BE_INTEGER')
    if premium is not None and (type(premium) not in (int,float) or not math.isfinite(premium) or premium<0):reasons.append('INVALID_PREMIUM')
    if mode=='live' and not live_confirmed:reasons.append('LIVE_RISK_NOT_OWNER_CONFIRMED')
    if any(r!='LIVE_RISK_NOT_OWNER_CONFIRMED' for r in reasons):return {'ready':False,'live_ready':False,'paper_ready':False,'mode':mode,'reasons':reasons,'exposure_from_reported_records_usd':exposure,'limits':config,'basis':'Paper ledger only' if mode=='paper' else 'AEGIS reports only, not brokerage balance'}
    if config.get('max_exposure_usd') is not None and exposure>=config['max_exposure_usd']:reasons.append('EXPOSURE_LIMIT')
    if premium is not None and config.get('max_trade_premium_usd') is not None and premium>config['max_trade_premium_usd']:reasons.append('TRADE_PREMIUM_LIMIT')
    if premium is not None and exposure+premium>config['max_exposure_usd']:reasons.append('PROJECTED_EXPOSURE_LIMIT')
    # Realized daily loss/cooldowns must be reconciled from dated records, never assumed zero.
    # Use the US-market day, including summer/winter offsets; UTC midnight is not a reset.
    if config.get('daily_reconciled_date')!=clock.astimezone(ZoneInfo('America/New_York')).date().isoformat():reasons.append('DAILY_RISK_RECONCILIATION_REQUIRED')
    if daily_loss>=config['max_daily_loss_usd']:reasons.append('DAILY_CIRCUIT_BREAKER')
    if streak>=config['max_consecutive_losses']:reasons.append('LOSS_STREAK_COOLDOWN')
    return {'ready':not reasons,'paper_ready':mode=='paper' and not reasons,'live_ready':mode=='live' and live_confirmed and not reasons,'mode':mode,'reasons':reasons,'exposure_from_reported_records_usd':exposure,'limits':config,'basis':'Paper ledger only' if mode=='paper' else 'AEGIS reports only, not brokerage balance'}
