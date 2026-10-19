"""Authenticated actual-fill questions; confirmation delegates to the existing ledger command."""
import json,io,contextlib,hashlib
from datetime import datetime,timezone
from decimal import Decimal
from data.models import stamp
from core.storage import ROOT
def begin(store,signal,tenant='owner',now=None):
    now=now or datetime.now(timezone.utc)
    if tenant!='owner':raise ValueError('OWNER_ONLY_PAPER_IDEA')
    c=signal.get('option_contract')
    from core.signals import option_quote_valid
    if not c or not option_quote_valid(c.get('quote',{}),now):raise ValueError('REAL_OPTION_QUOTE_REQUIRED')
    store.put('fill_flow:'+tenant,{'step':'quantity','contract':c['symbol'],'signal_id':signal['signal_id'],'signal':signal,'expires_at':signal['signal_expiry']})
    return 'How many contracts did you actually buy? /fill quantity NUMBER. No order is placed.'
def execute(store,text,tenant,event_id,now=None):
    now=now or datetime.now(timezone.utc);f=store.get('fill_flow:'+tenant)
    if not f or stamp(f['expires_at'])<=now:return 'Fill flow expired. Use /option_bought for a past actual fill; never infer a suggested fill.'
    action,_,value=text.partition(' ')
    if action=='cancel':store.put('fill_flow:'+tenant,{});return 'Fill flow cancelled; no holding created.'
    if action!=f.get('step'):return 'Current question: '+f.get('step','complete')+'. Use /fill '+f.get('step','')+' VALUE'
    marker='fill-step-'+hashlib.sha256((tenant+event_id).encode()).hexdigest()[:32]
    if store.get(marker):return 'Fill step already processed.'
    if action=='quantity':
        q=int(value)
        if not 1<=q<=100000:raise ValueError('INVALID_QUANTITY')
        f['quantity']=q;f['step']='premium';message='Your actual premium per share? /fill premium PRICE'
    elif action in ('premium','fees'):
        from options.ledger import amount
        n=amount(value)
        if action=='premium' and n<=0:raise ValueError('INVALID_PREMIUM')
        f[action]=str(n);f['step']='fees' if action=='premium' else 'time';message='Total actual fees USD? /fill fees AMOUNT' if action=='premium' else 'Actual fill time with timezone? /fill time YYYY-MM-DDTHH:MM:SS-04:00'
    elif action=='time':
        t=stamp(value)
        if t>now or t<stamp(f['signal']['timestamp']):raise ValueError('FILL_TIME_OUTSIDE_IDEA')
        f['filled_at']=t.astimezone(timezone.utc).isoformat();f['step']='confirm';message='Confirm actual '+str(f['quantity'])+' × '+f['premium']+' × 100 + '+f['fees']+' fees for '+f['contract']+'? /fill confirm yes'
    elif action=='confirm':
        if value.lower()!='yes':return 'Not confirmed. /fill confirm yes or /fill cancel'
        import options.command as command
        request={'command':'option_bought','id':event_id,'tenant':None if tenant=='owner' else tenant,'signal_id':f['signal_id'],'text':' '.join([f['contract'],str(f['quantity']),f['premium'],f['fees'],f['filled_at']])}
        output=io.StringIO()
        with contextlib.redirect_stdout(output):command.main(request)
        message=output.getvalue().strip()
        if message.startswith('REPORT NOT RECORDED'):return message
        s=f['signal'];op=s.get('option_plan') or {};plan={k:s.get(k) for k in ('invalidation','t1','t2')}
        plan.update(underlying_entry=s['spy_price'],signal_id=s['signal_id'],horizon=s.get('horizon'),source='USER_CONFIRMED_FILL',stop_bar_minutes=5,actual_entry=float(f['premium']),max_hold_until=op.get('max_hold_until'),option_t1=op.get('t1_bid'),option_t2=op.get('t2_bid'),option_stop=op.get('stop_bid'))
        if op.get('stop_bid') is not None:plan['estimated_loss_from_actual_fill']=(float(f['premium'])-op['stop_bid'])*100*f['quantity']+float(f['fees'])+.65*f['quantity']
        store.put('plan:'+tenant+':'+f['contract'],plan);f['step']='complete';message+='\nPrivate review plan created from your actual fill. Targets remain estimates from the idea; warnings require fresh data.'
    else:return 'Flow complete; use /option_positions.'
    store.put(marker,{'processed_at':now.isoformat()});store.put('fill_flow:'+tenant,f);return message
