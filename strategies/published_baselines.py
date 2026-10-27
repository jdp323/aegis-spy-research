"""Original deterministic implementations of published mathematical rules.

No external source code or order execution is imported. See research source notes.
These functions are shared by replay and read-only production comparisons.
"""
from statistics import mean
from datetime import datetime, timezone
from core.sessions import ET

VERSION='published-spy-baselines-v1'

def concretum_signal(today, previous_days, previous_close, dividend):
    """IMP decision only: prior same-clock absolute-open moves, VWAP, 30m cadence.

    Missing dividends are unavailable, never implicitly zero. Vol-target sizing,
    leverage and the separate overnight mean-reversion sleeve are not reproduced.
    """
    if not today or dividend is None or previous_close is None:return dict(status='UNAVAILABLE',reason='dividend-adjusted prior close and completed bars required')
    minute=len(today)
    if minute%30:return dict(status='ABSTAIN',reason='between registered 30-minute decisions')
    last=today[-1];slot=datetime.fromtimestamp(last['timestamp'],timezone.utc).astimezone(ET).time()
    moves=[]
    for day in previous_days[-14:]:
        b=next((r for r in day if datetime.fromtimestamp(r['timestamp'],timezone.utc).astimezone(ET).time()==slot),None)
        if b and day[0]['open']>0:moves.append(abs(b['close']/day[0]['open']-1))
    if len(moves)<13:return dict(status='UNAVAILABLE',reason='13 genuine prior same-clock sessions required')
    volume=sum(b['volume'] for b in today)
    if volume<=0:return dict(status='UNAVAILABLE',reason='VWAP volume unavailable')
    # Published VWAP is typical price * volume. No future same-day candles.
    vwap=sum((b['high']+b['low']+b['close'])/3*b['volume'] for b in today)/volume
    sigma=mean(moves);opening=today[0]['open'];prior=previous_close-dividend
    upper=max(opening,prior)*(1+sigma);lower=min(opening,prior)*(1-sigma)
    side=1 if last['close']>upper and last['close']>vwap else -1 if last['close']<lower and last['close']<vwap else 0
    return dict(status='RESEARCH',side=side,upper=upper,lower=lower,vwap=vwap,sigma=sigma,
        version=VERSION,fill_rule='next observation after decision plus declared delay',option_profitability='UNAVAILABLE')

def first_last(today, previous_close, vix=None, require_vix=True):
    slots={datetime.fromtimestamp(b['timestamp'],timezone.utc).astimezone(ET).strftime('%H:%M'):b for b in today}
    if any(k not in slots for k in ('10:00','15:00','15:30')) or previous_close is None:return dict(status='UNAVAILABLE',reason='required completed observations missing')
    # 15:30 opening value is known then; callers must only pass bars completed by
    # evaluation. A delayed evaluation is an explicit adaptation, not 15:30 fill.
    if require_vix and vix is None:return dict(status='UNAVAILABLE',reason='contemporaneous VIX missing')
    a=slots['10:00']['open']-previous_close;b=slots['15:30']['open']-slots['15:00']['open']
    side=(1 if a>0 and b>0 else -1 if a<0 and b<0 else 0) if not require_vix or vix>=20 else 0
    return dict(status='RESEARCH',side=side,version=VERSION,adaptation='completed-bar evaluation delay',option_profitability='UNAVAILABLE')

def opening_range(today):
    if len(today)<16:return dict(status='UNAVAILABLE',reason='first15 genuine opening minutes required')
    first=datetime.fromtimestamp(today[0]['timestamp'],timezone.utc).astimezone(ET)
    if (first.hour,first.minute)!=(9,30) or any(b['timestamp']-a['timestamp']!=60 for a,b in zip(today,today[1:])):return dict(status='UNAVAILABLE',reason='genuine contiguous opening range required')
    high=max(b['high'] for b in today[:15]);low=min(b['low'] for b in today[:15]);px=today[-1]['close']
    return dict(status='RESEARCH',side=1 if px>high else 0,trigger=high,stop=low,target=px+1.5*(px-low),
        version=VERSION,adaptation='SPY-only deterministic long ORB; no AI ranking, account sizing or execution')

def compare(rows, previous_days=(), previous_close=None, dividend=None):
    from strategies.concretum import decision
    return {'version':VERSION,'concretum_paper':decision(rows,previous_days,previous_close,dividend), 'concretum_article_diagnostic':concretum_signal(rows,previous_days,previous_close,dividend),
        'first_last_unfiltered':first_last(rows,previous_close,require_vix=False),
        'first_last_vix20':first_last(rows,previous_close), 'lumibot_spy_adaptation':opening_range(rows),
        'alerts_enabled':False,'live_signal_ready':False}

def compare_context(bar_context,now,corporate=None):
    from collections import defaultdict
    from features.indicators import normalize
    from core.sessions import market_session
    groups=defaultdict(list)
    for b in normalize(bar_context.get('rows',[]),now=now):
        groups[datetime.fromtimestamp(b['timestamp'],timezone.utc).astimezone(ET).date()].append(b)
    today=now.astimezone(ET).date();prior=[]
    for day,rows in sorted(groups.items()):
        if day>=today:continue
        session=market_session(datetime.combine(day,datetime.min.time(),ET).replace(hour=10))
        if len(rows)==session['close_minute']-570 and all(b['timestamp']-a['timestamp']==60 for a,b in zip(rows,rows[1:])):prior.append(rows)
    dividends=(corporate or {}).get('dividends',{}) if (corporate or {}).get('status')=='EX_DATE_COVERAGE_VERIFIED' and (corporate or {}).get('ex_date_coverage_verified') is True else {}
    return compare(groups.get(today,[]),prior,prior[-1][-1]['close'] if prior else None,dividends.get(today.isoformat()))
