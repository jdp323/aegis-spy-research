"""Deterministic tap-through demonstration. Writes only demo state/charts/transcripts."""
import json,hashlib,secrets,sys,math
from functools import lru_cache
from pathlib import Path
from datetime import datetime,timezone,timedelta
from decimal import Decimal
from core.storage import ROOT
from core.sessions import ET,market_session
from features.indicators import multi_timeframe,normalize,resample
from features.market_regime import classify
from strategies.spy_setups import detect
from core.signals import build
from core.verdict import short
from options.trade_plan import build as plan_build
from data.replay import ReplayProvider
PREFIX='🧪 DEMO — SIMULATED DATA'
SUFFIX='Nothing here is real.'
SCENARIOS=('call','put','swing','no-trade')
def wrap(text):return PREFIX+'\n'+text+'\n'+SUFFIX
def fixture(scenario='call',hour=10,minute=22):
    now=datetime(2026,10,8,hour,minute,tzinfo=ET).astimezone(timezone.utc);sign=-1 if scenario=='put' else 1
    days=[];d=now.astimezone(ET).date()
    while len(days)<12:
        t=datetime.combine(d,datetime.min.time(),ET)+timedelta(hours=10)
        if market_session(t)['active']:days.append(d)
        d-=timedelta(days=1)
    rows=[];daily=[]
    for index,day in enumerate(reversed(days)):
        start=datetime.combine(day,datetime.min.time(),ET)+timedelta(hours=9,minutes=30)
        count=int((now-start).total_seconds()/60) if day==now.astimezone(ET).date() else 390
        base=500+sign*(index-11)*10
        for m in range(count):
            px=base+sign*.025*m+sign*.3*math.sin(m/3)
            if day==now.astimezone(ET).date() and m>=count-12:px+=sign*.08*(m-(count-12))
            volume=1000*(2 if day==now.astimezone(ET).date() and m>=count-5 else 1)
            rows.append(dict(t=(start+timedelta(minutes=m)).astimezone(timezone.utc).isoformat(),o=px-sign*.01,h=px+.03,l=px-.03,c=px,v=volume,feed_quality='SIMULATED'))
    d=now.astimezone(ET).date()-timedelta(days=1)
    while len(daily)<65:
        t=datetime.combine(d,datetime.min.time(),ET)+timedelta(hours=10)
        if market_session(t)['active']:
            p=500-sign*len(daily)*.5;daily.append(dict(t=t.astimezone(timezone.utc).isoformat(),o=p-.1,h=p+.3,l=p-.3,c=p,v=100000,feed_quality='SIMULATED'))
        d-=timedelta(days=1)
    daily.reverse();px=rows[-1]['c']+sign*.04
    features=multi_timeframe(rows,daily,now,simulation=True);regime=classify(features['5m'],'DATA_OK')
    expiry='2026-10-14';strike=round(px);symbol='SPY261014'+('P' if sign==-1 else 'C')+f'{strike*1000:08d}'
    q=dict(provider='replay-simulated',symbol='SPY',source_timestamp=now.isoformat(),received_timestamp=now.isoformat(),quality='DATA_OK',entitlement='SIMULATED',feed_quality='SIMULATED',data_type='quote',payload={'bid':px-.01,'ask':px+.01,'mid':px})
    oq={**q,'symbol':symbol,'payload':dict(bid=2.35,ask=2.40,mid=2.375)}
    c=dict(symbol=symbol,type='P' if sign==-1 else 'C',strike=strike,expiry=expiry,bid=2.35,ask=2.4,mid=2.375,delta=sign*.5,gamma=.05,theta=-.03,vega=.10,iv=.2,volume=1000,oi=5000,greeks_timestamp=now.isoformat(),quote=oq)
    config=dict(allow_unvalidated_paper_trading=True,signal_expiry_seconds=600,options_risk={'max_trade_premium_usd':500},horizons={'scalp_minutes':60,'swing_enabled':scenario=='swing','swing_days':3})
    news=dict(quality='DATA_OK',risk='NORMAL',coverage_complete=True,coverage_through=(now+timedelta(days=7)).isoformat(),events=[],feed_quality='SIMULATED')
    real=build(features,regime,{'best_contract':c},q,news,market_session(now),{'ready':True},now,config).dict()
    # Demonstration view is an isolated copy. Original evaluated object retains all real rejections.
    data_only={'UNDERLYING_DATA_NOT_VERIFIED','OPTION_QUOTE_NOT_FRESH_VERIFIED','OPTION_QUOTE_NOT_VERIFIED','SIMULATED_DATA_FORBIDDEN'}
    remaining=[r for r in real['paper_blockers'] if r not in data_only]
    if remaining:raise ValueError('DEMO_FIXTURE_OTHER_GATE_FAILED: '+','.join(remaining))
    view=dict(real);view.update(direction='CALL' if sign==1 else 'PUT',feed_quality='SIMULATED',paper_eligible=True,paper_blockers=[],actionable=False,live_signal_ready=False,demo_only_data_gate_substitution=True)
    setup=detect(features,px);view.update(setup_type=setup['setup_type'],invalidation=setup['invalidation'],entry_condition='after a completed 5-minute close confirms '+setup['setup_type'].lower().replace('_',' '))
    if setup['invalidation'] is None:raise ValueError('DEMO_FIXTURE_SETUP_INVALID')
    dist=abs(px-setup['invalidation']);view.update(t1=px+sign*dist*1.5,t2=px+sign*dist*2,risk_reward=2)
    if scenario=='swing':view['setup_type']='TREND_CONTINUATION'
    view['option_plan']=plan_build(view,now,config,news,simulation=True);view['horizon']=view['option_plan']['horizon']
    replay=ReplayProvider(rows,q['payload'],{symbol:c},now)
    return dict(now=now,signal=view,real_evaluation=real,features=features,regime=regime,provider=replay,rows=rows,scenario=scenario)
def chart(f,path):
    vendor=str(ROOT/'.vendor')
    if vendor not in sys.path:sys.path.insert(0,vendor)
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    bars=resample(normalize(f['rows'],now=f['now'],simulation=True),5);bars=[b for b in bars if datetime.fromtimestamp(b['timestamp'],timezone.utc).astimezone(ET).date()==f['now'].astimezone(ET).date()]
    s=f['signal'];scenario=f.get('scenario','call')
    if scenario=='no-trade':
        for n,b in enumerate(bars):b.update(close=s['spy_price']+(.12 if n%2 else -.12),high=s['spy_price']+.2,low=s['spy_price']-.2)
    elif scenario=='swing':
        for n,b in enumerate(bars):b['close']+=.15*math.sin(n/2)
    fig,ax=plt.subplots(figsize=(8,4));ax.plot([b['close'] for b in bars],label='Synthetic SPY 5m');v=total=0;vw=[]
    for b in bars:v+=b['volume'];total+=(b['high']+b['low']+b['close'])/3*b['volume'];vw.append(total/v)
    ax.plot(vw,label='Synthetic bar VWAP')
    if scenario=='no-trade':
        ax.axhline(min(b['low'] for b in bars),linestyle='--',label='support (no entry)')
        ax.axhline(max(b['high'] for b in bars),linestyle='--',label='resistance (no entry)')
    else:
        for k in ('spy_price','invalidation','t1','t2'):ax.axhline(s[k],linestyle='--',label=k)
    ax.set_title(PREFIX.replace('🧪 ','')+' — '+('NO TRADE' if scenario=='no-trade' else scenario.upper()+' '+s['direction']));ax.legend(fontsize=8);fig.tight_layout();Path(path).parent.mkdir(parents=True,exist_ok=True);fig.savefig(path);plt.close(fig);return str(path)
def response(state,action='next',value='',root=ROOT):
    """Pure flow result except explicit chart generation. No production store/transport imports."""
    scenario=state.get('scenario','call');f=fixture('call' if scenario=='no-trade' else scenario);f['scenario']=scenario;s=f['signal'];plan=s['option_plan'];stage=state.get('stage',0)
    if action in SCENARIOS:state.update(scenario=action,stage=0);return response(state,'next',root=root)
    if action in ('stop','skipped'):state['stage']=-1;return wrap('Demo stopped; no position or real ledger was changed.')
    if action=='chart':
        p=chart(f,Path(root)/'daily_reports/charts'/('demo-'+state['nonce']+'.png'));return {'text':wrap('Generated synthetic SPY chart; levels and VWAP are fictional.'),'photo':p}
    if action=='bought':state['stage']=5;state['flow']='quantity';return wrap('Simulated fill — how many contracts? Reply /demo quantity 1')
    if action in ('quantity','premium','fees','time','confirm'):
        expected=state.get('flow')
        if action!=expected:return wrap('Complete the current question first: '+str(expected))
        if action=='quantity':
            q=int(value)
            if not 1<=q<=100:raise ValueError('INVALID_DEMO_QUANTITY')
            state['quantity']=q;state['flow']='premium';return wrap('Actual simulated fill premium? Reply /demo premium 2.40 (editable)')
        if action in ('premium','fees'):
            n=Decimal(value)
            if not n.is_finite() or n<0 or n>10000:raise ValueError('INVALID_DEMO_AMOUNT')
            state[action]=str(n);state['flow']='fees' if action=='premium' else 'time';return wrap('Total simulated fees? /demo fees 0.65' if action=='premium' else 'Fill time with offset? /demo time '+f['now'].isoformat())
        if action=='time':
            from data.models import stamp
            t=stamp(value);state['fill_time']=t.astimezone(timezone.utc).isoformat();state['flow']='confirm';return wrap('Confirm '+str(state['quantity'])+' × '+state['premium']+' × 100 + '+state['fees']+' fees at '+state['fill_time']+'? /demo confirm yes')
        if value.lower()!='yes':return wrap('Fill not confirmed. /demo confirm yes or /demo stop')
        cost=Decimal(state['premium'])*100*state['quantity']+Decimal(state['fees']);state['cost']=str(cost);state['flow']=None;state['stage']=5
        return wrap('Simulated cost = '+str(cost)+' USD. No actual position recorded. Tap Next for target and exit reviews.')
    if action=='sold':
        if 'cost' not in state:return wrap('First complete the simulated bought flow.')
        if not value:return wrap('Enter the simulated sale premium: /demo sold 3.10 (editable). Fees modeled at 0.65 total USD.')
        sale=Decimal(value)
        if not sale.is_finite() or sale<0:raise ValueError('INVALID_DEMO_SALE')
        proceeds=sale*100*state['quantity']-Decimal('.65');net=proceeds-Decimal(state['cost']);state['stage']=8
        return wrap('Sale '+str(sale)+' × 100 × '+str(state['quantity'])+' − 0.65 = '+str(proceeds)+' USD; net = '+str(proceeds)+' − '+state['cost']+' = '+str(net)+' USD.\nDemo prices are fictional; this is not a backtest or evidence of profit.')
    if action=='exit':state['stage']=6;stage=6
    if action=='v5':
        from ops.day_simulation import run_scenario
        r=run_scenario('normal',f['now'].astimezone(ET).date())
        from monitoring.message_format import score_summary_text as score_text
        return wrap('V5 message schedule example\n'+score_text(r['score']))
    if action=='status':return wrap('Demo stage '+str(stage)+'; reported holdings remain unchanged.')
    if scenario=='no-trade':
        blocks=['NEWS_UNAVAILABLE_OR_BLACKOUT','PROXY_FRESH_FEED_AND_31_BAR_TAIL_REQUIRED','PREMIUM_ABOVE_CAP','FEED_MISMATCH']
        if stage<len(blocks):
            c=dict(s,paper_blockers=[blocks[stage]],paper_eligible=False);state['stage']=stage+1;return wrap(short(c,f['now'],trend='MIXED',simulation=True))
        state['stage']=min(stage+1,13)
        return wrap(v5_scene('choppy',max(0,stage-5))) if stage>=5 else wrap('Premium target missed because spread widened: a fictional last trade is not an executable bid. No-trade cases completed; no evidence was collected.')
    texts=[
      'Choose a fictional Call, Put, Swing or No-trade day. Tap Next; no timers, no real trades.',
      '09:15 ET — MORNING EXAMPLE\nPrice/news outlook is illustrative; synthetic '+('DOWN' if scenario=='put' else 'UP')+' evidence. Scheduled calendar context is fictional.',
      short(dict(s,paper_eligible=False,paper_blockers=['PROXY_CONFIRMATION_MISSING']),f['now'].replace(hour=14,minute=1),simulation=True),
      short(s,f['now'],simulation=True),
      'Use I bought to enter a simulated quantity, premium, fees and time. Skip does not create a holding.',
      f"10:40 ET — T1 REACHED (synthetic)\nSPY {s['t1']:.2f} / option bid est. {plan['t1_bid']:.2f}. Consider taking profit. A demo trailing stop is moved explicitly to the entry level; no silent stop changes.",
      f"{'Day two' if scenario=='swing' else '11:05 ET'} — EXIT REVIEW\nSPY returns through the demo trailing level {s['spy_price']:.2f}; option bid est. {plan['stop_bid']:.2f}. {'Overnight gap risk; time stop in days.' if scenario=='swing' else 'Review a manual exit.'}",
      'I sold asks for your simulated sale premium. /demo sold 3.10; a quote is not a fill.',
      'Demo prices are fictional; this is not a backtest or evidence of profit.'
    ]
    result=v5_scene(scenario,stage-8) if stage>=8 else texts[min(stage,8)];state['stage']=min(stage+1,17);return wrap(result)
@lru_cache(maxsize=2)
def v5_result(scenario):
    from ops.day_simulation import run_scenario
    return run_scenario('choppy' if scenario in ('choppy','no-trade') else 'normal',datetime(2026,10,9).date())
def v5_scene(scenario,stage):
    from monitoring.message_format import score_summary_text as score_text
    r=v5_result(scenario)
    if stage>=9:return 'V5 /score example\n'+score_text(r['score'])+'\nDemo prices are fictional; not a backtest or evidence of profit.'
    types=('PREOPEN','TREND_LINE','TREND_LINE','SPY_IDEA','IDEA_UPDATE','IDEA_UPDATE','IDEA_UPDATE','IDEA_UPDATE','RECAP')
    matches=[e for e in r['timeline'] if e['alert_type']==types[stage]]
    if stage==1:
        early=[e for e in matches if 'EARLY READ' in e['text']]
        matches=early or matches
    if stage==2:matches=[e for e in matches if 'EARLY READ' not in e['text']]
    if stage in (4,5):
        condition='ENTRY TRIGGERED' if stage==4 else 'TARGET_1_HIT'
        matches=[e for e in matches if condition in e['text']]
    if stage in (5,6,7):return v5_variant(('TARGET_1_HIT','STOP HIT','IDEA EXPIRED')[stage-5])
    return matches[0]['text'] if matches else 'NO TRADE — no confirmed setup in this simulated scenario.'

def v5_variant(condition):
    """Teaching paths go through the actual tracker with memory-only simulated bars."""
    from backtesting.idea_tracker import IdeaTracker
    from ops.day_simulation import MemoryStore,inputs,config
    from core.idea_service import context,candidates
    now=datetime(2026,10,9,9,46,tzinfo=ET).astimezone(timezone.utc);s=MemoryStore();inputs(s,now)
    ctx=context(s,now,True);i=candidates(ctx,{'quality':'DATA_OK','risk':'NORMAL'},config(),now,True)[0][0]
    tracker=IdeaTracker(simulation=True)
    if condition=='IDEA EXPIRED':i['entry_mode']='TRIGGER'
    tracker.register(i,ctx['quote'],now,True)
    if condition=='IDEA EXPIRED':changes=tracker.observe([],now+timedelta(minutes=11))
    else:
        entry=tracker.positions()[0]['fill_price'];b={'t':now.isoformat(),'o':entry,'h':i['t1']+.02 if condition=='TARGET_1_HIT' else entry+.02,'l':entry-.01 if condition=='TARGET_1_HIT' else i['invalidation']-.02,'c':i['t1'] if condition=='TARGET_1_HIT' else i['invalidation'],'feed_quality':'SIMULATED'}
        changes=tracker.observe([b],now+timedelta(minutes=2),feed_quality='SIMULATED')
    expected={'TARGET_1_HIT':'TARGET_1_HIT','STOP HIT':'STOP_HIT','IDEA EXPIRED':'IDEA_EXPIRED'}[condition]
    if not any(kind==expected for _,kind in changes):raise ValueError('DEMO_TRACKER_VARIANT_NOT_REACHED')
    p=tracker.positions()[0];return 'EXIT REVIEW — '+condition+' (fictional teaching variant; actual memory tracker)\nSPY entry %.2f · stop %.2f · T1 %.2f · T2 %.2f'%(i['entry'],i['invalidation'],i['t1'],i['t2'])+'\nRecorded state: '+p['status']+('; trailing suggestion: review entry stop; original recorded stop unchanged.' if condition=='TARGET_1_HIT' else '')+'\nUNDERLYING (not option P&L). Unvalidated research. No order placed.'

def run(data,root=ROOT):
    tenant=data.get('tenant') or 'owner'
    if tenant!='owner' and not __import__('re').fullmatch('[a-f0-9]{24}',tenant):raise ValueError('INVALID_DEMO_TENANT')
    folder=Path(root)/'monitoring/demo_sessions';folder.mkdir(parents=True,exist_ok=True);path=folder/(tenant+'.json');now=datetime.now(timezone.utc)
    state=json.loads(path.read_text()) if path.exists() else {}
    text=data.get('text','');action,_,value=text.partition(' ');action=action.lower() or 'start'
    if action=='start':state={'nonce':secrets.token_hex(12),'stage':0,'scenario':'call','expires_at':(now+timedelta(hours=1)).isoformat(),'used':[]}
    if not state:return {'text':wrap('Use /demo start to begin.')}
    if data.get('nonce'):
        if data['nonce']!=state.get('nonce') or now>=datetime.fromisoformat(state['expires_at']):return {'text':wrap('Demo button expired. /demo start')}
        id=str(data.get('callback_id',''))
        if not id or id in state['used']:return {'text':wrap('Demo action already processed.')}
        state['used'].append(id);state['used']=state['used'][-100:]
    try:r=response(state,'next' if action=='start' else action,value,root)
    except (ValueError,KeyError):r=wrap('Invalid demo input; complete the current question or /demo stop.')
    tmp=path.with_suffix('.pending');tmp.write_text(json.dumps(state));tmp.replace(path)
    out=r if isinstance(r,dict) else {'text':r};nonce=state['nonce']
    actions=[('Call trade','call'),('Put trade','put'),('Swing trade','swing'),('No-trade day','no-trade'),('Stop','stop')] if action=='start' else [('Next ▶','next'),('✅ I bought','bought'),('📊 Chart','chart'),('🚫 Skip','skipped')]
    out['reply_markup']={'inline_keyboard':[[{'text':t,'callback_data':'demo:'+nonce+':'+a} for t,a in actions[:3]],[{'text':t,'callback_data':'demo:'+nonce+':'+a} for t,a in actions[3:]]]}
    return out
class FakeTransport:
    def __init__(self):self.messages=[]
    def send(self,result):
        text=result.get('text') if isinstance(result,dict) else result
        if not text.startswith(PREFIX) or not text.endswith(SUFFIX):raise ValueError('UNLABELLED_DEMO_MESSAGE')
        self.messages.append(text)
        return text

def console(root=ROOT):
    transport=FakeTransport()
    lines=['# Demonstration transcript — EXAMPLE; simulated, not evidence','']
    for scenario in SCENARIOS:
        state={'nonce':'fixture'+scenario,'scenario':scenario,'stage':0};lines+=['## '+scenario.upper()]
        for _ in range(5):lines += ['```',transport.send(response(state,root=root)),'```']
        if scenario!='no-trade':
            for action,value in [('bought',''),('quantity','1'),('premium','2.40'),('fees','0.65'),('time','2026-10-08T10:22:00-04:00'),('confirm','yes'),('next',''),('exit',''),('sold','3.10'),('next','')]:lines+=['```',transport.send(response(state,action,value,root)),'```']
        for scene in range(10):lines+=['```',transport.send(wrap(v5_scene('choppy' if scenario=='no-trade' else scenario,scene))),'```']
        f=fixture('call' if scenario=='no-trade' else scenario);f['scenario']=scenario;chart(f,Path(root)/'daily_reports/charts'/('demo-console-'+scenario+'.png'))
    p=Path(root)/'daily_reports'/('DEMO_TRANSCRIPT_'+datetime.now(timezone.utc).date().isoformat()+'.md');p.write_text('\n'.join(lines),encoding='utf-8');return p
if __name__=='__main__':
    if sys.argv[1:]==['--console']:print(console())
    else:print(json.dumps(run(json.load(sys.stdin)),ensure_ascii=False))
