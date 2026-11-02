"""At most 25 exact owner receipt files, no recursive ledger/report scan."""
import json
from core.sessions import ET,market_session
from data.models import stamp

def summary(root,now):
    session=market_session(now);day=now.astimezone(ET).date().isoformat();expected=list(range(585,session['close_minute'],15));accepted=timely=0
    for minute in expected:
        path=root/'logs/notifications'/('v5-trend-'+day+'-'+str(minute)+'.json')
        try:
            if path.stat().st_size>65536:continue
            row=json.loads(path.read_text());at=stamp(row['accepted_at']);slot=now.astimezone(ET).replace(hour=minute//60,minute=minute%60,second=0,microsecond=0)
            if row.get('status')=='TELEGRAM_ACCEPTED':accepted+=1;timely+=0<=(at-slot).total_seconds()<=30
        except (OSError,ValueError,KeyError,TypeError):continue
    return {'expected':len(expected),'accepted':accepted,'timely':timely,'phone_delivery_verified':False,'missing':len(expected)-accepted,'late_or_missing':len(expected)-timely}
