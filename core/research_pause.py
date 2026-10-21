"""Deterministic research pause episodes; never private actual-position losses."""
from copy import deepcopy
from datetime import timedelta
from data.models import stamp
from core.sessions import ET

VERSION='research-loss-episodes-v2'

def advance(previous, closed, now, threshold=3, minutes=60):
    state=deepcopy(previous or {'version':VERSION,'seen':[],'streak':0,'episode':None})
    state['version']=VERSION;state.setdefault('seen',[]);state.setdefault('streak',0);state.setdefault('qualifying_ids',[])
    seen=set(state['seen']); warnings=[]
    episode=state.get('episode')
    fresh=sorted((r for r in closed if r.get('status')=='CLOSED' and stamp(r['closed_at'])<=now and r['signal_id'] not in seen),key=lambda r:(r['closed_at'],r['signal_id']))
    for row in fresh:
        seen.add(row['signal_id'])
        # Preserve strategy deterioration measurement even for unalerted research.
        # While paused each outcome is consumed, but cannot roll the same episode.
        if episode and stamp(row['closed_at'])<stamp(episode['end']):continue
        if episode and stamp(row['closed_at'])>=stamp(episode['end']):state['streak']=0;state['qualifying_ids']=[];episode=None
        state['streak']=state['streak']+1 if row.get('r_multiple',0)<0 else 0
        state['qualifying_ids']=(state['qualifying_ids']+[row['signal_id']]) if row.get('r_multiple',0)<0 else []
        if state['streak']>=threshold:
            start=stamp(row['closed_at']);end=start+timedelta(minutes=minutes)
            episode=dict(id=row['signal_id'],start=start.isoformat(),end=end.isoformat(),
                reason=str(threshold)+' consecutive closed underlying research losses; not your trading losses',
                cause_ids=state['qualifying_ids'][-threshold:])
            state['streak']=0;state['qualifying_ids']=[]
            if end>now:warnings.append('COOL-OFF — Research entries paused '+start.astimezone(ET).strftime('%H:%M')+'–'+end.astimezone(ET).strftime('%H:%M ET')+' — '+episode['reason']+'. Trend/watch context continues.')
    state['seen']=sorted(seen);state['episode']=episode
    active=bool(episode and now<stamp(episode['end']))
    return state, active, warnings
