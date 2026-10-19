"""Human-readable readiness; configured credentials are not fresh data."""
from data.models import stamp
from datetime import datetime,timezone
from core.sessions import ET

def clock_text(snapshot,now=None):
    now=now or datetime.now(timezone.utc);lines=[]
    ntp=snapshot.get('ntp_clock') or {}
    if ntp:lines.append('NTP: '+ntp.get('state','UNAVAILABLE')+' | offset '+str(ntp.get('offset_seconds','UNAVAILABLE'))+'s | skew budget '+str(snapshot.get('skew_budget_seconds','UNAVAILABLE'))+'s (source timestamps preserved)')
    for feed,data in (snapshot.get('clock_health') or {}).items():
        if not isinstance(data,dict) or data.get('state')!='FUTURE_TIMESTAMP_REJECTED':continue
        try:
            age=(now-stamp(data['at'])).total_seconds()
            if 0<=age<=120:lines.append(feed.upper()+' clock: excess future market timestamps rejected; verify Windows time synchronization. Configured tolerance never changes source timestamps.')
            else:lines.append(feed.upper()+' clock: historical future-timestamp rejection; current clock health UNVERIFIED.')
        except (KeyError,ValueError,TypeError):lines.append(feed.upper()+' clock: diagnostic timestamp UNVERIFIED.')
    return '\n'.join(lines) or 'Clock diagnostics: no recent rejection recorded; synchronization is not established by this alone.'

def text_for(snapshot,now=None):
    now=now or datetime.now(timezone.utc)
    def quote_line(label,q):
        q=q or {}
        try:
            source=stamp(q['source_timestamp']);age=(now-source).total_seconds()
            detail=' | source '+source.astimezone(ET).strftime('%Y-%m-%d %H:%M:%S ET')+' | age %.1fs'%age
        except (ValueError,KeyError,TypeError):detail=' | no verified quote timestamp'
        return label+': '+str(q.get('quality','DATA_INCOMPLETE'))+detail
    streams=snapshot.get('streams') or {}
    def stream_line(feed):
        h=streams.get(feed) or {};state=h.get('state','UNAVAILABLE')
        try:
            age=(now-stamp(h['at'])).total_seconds()
            if not 0<=age<=30:state+=' (heartbeat stale)'
        except (ValueError,KeyError,TypeError):state+=' (heartbeat unverified)'
        return feed.upper()+' stream: '+state
    provider=snapshot.get('provider') or {}
    live=snapshot.get('live_trend') or {}
    available=snapshot.get('data_availability') or {}
    return '\n'.join([
        'AEGIS DATA HEALTH',
        'Session: '+str((snapshot.get('session') or {}).get('state','UNAVAILABLE')),
        'Provider configuration: '+str(provider.get('status','UNAVAILABLE'))+' (configuration only)',
        clock_text(snapshot,now),
        stream_line('iex'),quote_line('IEX single-exchange quote',snapshot.get('research_underlying')),
        stream_line('sip'),quote_line('SIP consolidated quote',snapshot.get('underlying')),
        stream_line('opra'),'Options chain: '+str(available.get('options','DATA_INCOMPLETE')),
        'News: '+str(available.get('news','DATA_INCOMPLETE')),
        'Live trend: '+str(live.get('status','UNAVAILABLE'))+' — '+str(live.get('reason','not verified')),
        'Full live trend needs 31 contiguous completed current-session minute bars and a quote no older than 5s.',
        'IEX is not consolidated NBBO, total-market volume or OPRA. Idle option subscriptions do not prove entitlement.',
        'Public historical bars remain separately labeled; they do not replace live quotes.',
        'Live option entry/exit alerts: DISABLED. /trend recalculates; /setup explains trade blockers.'
    ])
