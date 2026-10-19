"""Matched-clock random-direction benchmark; requires the actual opposite contract quote."""
import hashlib,random,copy
from core.signals import option_quote_valid
from options.trade_plan import build as plan_build
from backtesting.paper_engine import PaperEngine
def open_baseline(path,signal,opposite,config,news,now):
    if not signal.get('paper_eligible'):return 'NO_ELIGIBLE_SIGNAL'
    sign=1 if signal['direction']=='CALL' else -1
    chosen=random.Random(int(signal['signal_id'],16)).choice((-1,1))
    c=signal['option_contract'] if chosen==sign else opposite
    if not c or not option_quote_valid(c.get('quote',{}),now):return 'OPPOSITE_REAL_QUOTE_UNAVAILABLE'
    s=copy.deepcopy(signal);s['signal_id']=hashlib.sha256((signal['signal_id']+'random-direction-v1').encode()).hexdigest()[:24];s['direction']='CALL' if chosen==1 else 'PUT';s['option_contract']=c;s['benchmark']='MATCHED_CLOCK_RANDOM_DIRECTION_V1';s['strategy_version']='benchmark-random-direction-v1'
    px=s['spy_price'];original_stop=abs(px-s['invalidation']);t1=abs(s['t1']-px);t2=abs(s['t2']-px)
    s.update(invalidation=px-chosen*original_stop,t1=px+chosen*t1,t2=px+chosen*t2)
    try:s['option_plan']=plan_build(s,now,config,news);s['horizon']=s['option_plan']['horizon']
    except ValueError:return 'BASELINE_PLAN_NOT_VERIFIED'
    engine=PaperEngine(path,kind='paper_baseline')
    try:return engine.open(s,c['quote'],slippage=config['paper_slippage_per_share'],fee=config['paper_fee_per_contract'],now=now)
    finally:engine.store.close()
