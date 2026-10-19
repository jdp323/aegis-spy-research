"""Versioned official US equity calendar. Unknown years fail closed."""
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from core.exchange_calendar import HOLIDAYS,EARLY,YEARS,VERSION
ET=ZoneInfo('America/New_York')
def market_session(now=None):
    if now is not None and now.tzinfo is None:raise ValueError('AWARE_TIME_REQUIRED')
    t=(now or datetime.now(timezone.utc)).astimezone(ET);minute=t.hour*60+t.minute;day=t.date().isoformat()
    out={'timestamp':t.astimezone(timezone.utc).isoformat(),'timestamp_et':t.isoformat(),'date':day,'timezone':'America/New_York','calendar_version':VERSION,'active':False,'early_close':day in EARLY,'close_minute':780 if day in EARLY else 960}
    if t.year not in YEARS:return {**out,'state':'CLOSED','quality':'DATA_INVALID','reason':'CALENDAR_REFRESH_REQUIRED'}
    if day in HOLIDAYS:state='HOLIDAY'
    elif t.weekday()>4 or minute<240 or minute>=1200:state='CLOSED'
    elif minute<570:state='PREMARKET'
    elif minute>=out['close_minute']:state='AFTER_HOURS'
    elif minute<600:state='OPENING'
    elif minute>=out['close_minute']-30:state='CLOSING'
    elif day in EARLY:state='EARLY_CLOSE'
    else:state='REGULAR'
    return {**out,'state':state,'quality':'DATA_OK','active':state in ('OPENING','REGULAR','CLOSING','EARLY_CLOSE')}
