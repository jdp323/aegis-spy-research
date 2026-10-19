"""V5 research-only defaults; never changes the paper or live risk policy."""
from core.simple_config import number
SETUPS=('OPENING_RANGE_BREAKOUT','OPENING_RANGE_BREAKDOWN','VWAP_RECLAIM','VWAP_REJECTION','TREND_CONTINUATION','SUPPORT_BOUNCE','RESISTANCE_REJECTION','BREAKOUT_RETEST')
DEFAULTS={'idea_engine_enabled':True,'trend_lines_silent':True,'idea_daily_cap':None,'idea_cooldown_minutes':10,'cooloff_minutes':60,'cooloff_losses':3,'min_rr':1.5,'early_session_ideas':True,'rough_risk_delta_range':[.4,.6],'premium_cap_mode':'warn','report_time':'09:15','recap_time':'16:15','idea_runaway_limit':40,'idea_stop_atr_fraction':.5}
def settings(config):
    c={**DEFAULTS,**{k:config[k] for k in DEFAULTS if k in config}}
    c['setup_enabled']={k:True for k in SETUPS};c['setup_enabled'].update(config.get('setup_enabled',{}))
    for k in ('idea_engine_enabled','trend_lines_silent','early_session_ideas'):
        if type(c[k]) is not bool:raise ValueError('INVALID_IDEA_BOOLEAN')
    if c['idea_daily_cap'] is not None and (type(c['idea_daily_cap']) is not int or not 1<=c['idea_daily_cap']<=40):raise ValueError('INVALID_IDEA_CAP')
    for k,lo,hi in [('idea_cooldown_minutes',1,120),('cooloff_minutes',1,240),('cooloff_losses',1,10),('idea_runaway_limit',1,40)]:
        if type(c[k]) is not int or not lo<=c[k]<=hi:raise ValueError('INVALID_IDEA_COOLDOWN')
    if not number(c['min_rr'],1.5,5) or not number(c['idea_stop_atr_fraction'],.5,2):raise ValueError('INVALID_IDEA_LEVEL_POLICY')
    d=c['rough_risk_delta_range']
    if not isinstance(d,list) or len(d)!=2 or not all(number(x,0,1) for x in d) or not 0<d[0]<=d[1]:raise ValueError('INVALID_DELTA_GUIDELINE')
    if c['premium_cap_mode'] not in ('warn','reject'):raise ValueError('INVALID_PREMIUM_CAP_MODE')
    for key in ('report_time','recap_time'):
        try:h,m=map(int,c[key].split(':'))
        except (ValueError,AttributeError):raise ValueError('INVALID_REPORT_TIME')
        if not 0<=h<24 or not 0<=m<60:raise ValueError('INVALID_REPORT_TIME')
    if not 540<=sum(x*y for x,y in zip(map(int,c['report_time'].split(':')),(60,1)))<570:raise ValueError('INVALID_PREOPEN_TIME')
    if c['recap_time']!='16:15':raise ValueError('UNSUPPORTED_RECAP_TIME')
    if set(c['setup_enabled'])!=set(SETUPS) or any(type(x) is not bool for x in c['setup_enabled'].values()):raise ValueError('INVALID_SETUP_FLAGS')
    if not isinstance(config.get('negative_setup_overrides',[]),list) or any(x not in SETUPS for x in config.get('negative_setup_overrides',[])):raise ValueError('INVALID_NEGATIVE_OVERRIDE')
    return c
