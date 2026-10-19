"""Owner callback actions, bound to recorded signal/expiry and durable one-use actions."""
import json,sys,hashlib
from datetime import datetime,timezone
from core.storage import Store,ROOT
from data.models import stamp
def execute(data,store=None,now=None):
 now=now or datetime.now(timezone.utc);own=store is None;s=store or Store()
 try:
  if data.get('tenant') not in (None,'owner'):raise ValueError('OWNER_ONLY')
  id=data['signal_id'];action=data['action']
  if action not in ('skip','chart','log','more'):raise ValueError('INVALID_ACTION')
  signal=next((v for v in s.events('paper_candidate',1000) if v['signal_id']==id),None)
  if not signal or stamp(signal['signal_expiry'])<=now or s.get('paper_terminal:'+id):raise ValueError('SIGNAL_EXPIRED_OR_INVALIDATED')
  key='paper-action-'+hashlib.sha256((id+signal['strategy_version']+action).encode()).hexdigest()[:32]
  if not s.event(key,'paper_action',{'signal_id':id,'action':action,'at':now.isoformat()}):return {'text':'Paper action already handled; no duplicate change.'}
  s.audit(key,'paper_callback','owner',{'signal_id':id,'action':action})
  if action=='more':
   if signal.get('strategy_version','').startswith('spy-ideas-') or signal.get('horizon_id') in ('H60','H120','SESSION'):
    from monitoring.message_format import number,et,plain
    return {'text':'PAPER / UNVALIDATED — SPY idea details\nID '+plain(signal['signal_id'])+'; setup '+plain(signal['setup_type'])+'\nConfirmation trigger: '+number(signal.get('trigger_level',signal.get('trigger')))+'\nReference midpoint: '+number(signal.get('reference_midpoint',signal.get('spy_price')))+'\nModeled entry fill: '+number(signal.get('modeled_entry_fill'))+'\nSPY invalidation '+number(signal['invalidation'])+'; targets '+number(signal['t1'])+' / '+number(signal['t2'])+'\nEntry validity '+et(signal['signal_expiry'])+'; full-exit review '+et(signal.get('max_hold_until'))+'\n'+plain(signal.get('score_meaning','Mandatory confirmation checks, not a probability.'))+'\n'+'\n'.join(plain(x,180) for x in signal.get('explanation',[]))+'\nData: '+plain(signal['feed_quality'])+'; option contract: '+plain((signal.get('option_contract') or {}).get('symbol','UNAVAILABLE'))+'\nUNDERLYING (not option P&L). Your actual reported fills remain separate and private. No order placed.'}
   from core.verdict import why
   return {'text':'PAPER / UNVALIDATED\n'+why(signal)}
  if action=='skip':s.put('paper_skip:'+id,{'at':now.isoformat()});return {'text':'PAPER / UNVALIDATED — skipped for your manual review. No reported holding or order created. The theoretical paper record stays preserved.'}
  if action=='chart':
   from core.paper_chart import generate
   try:path=generate(s,signal,now)
   except (ValueError,ImportError):return {'text':'PAPER / UNVALIDATED — chart unavailable: sufficient current-session bars or renderer are missing.'}
   return {'text':'PAPER / UNVALIDATED — SPY completed 5-minute chart, VWAP and research levels. No orders.','photo':str(path)}
  from core.signals import option_quote_valid
  c=signal.get('option_contract')
  if not c or not option_quote_valid(c.get('quote',{}),now):return {'text':'PAPER / UNVALIDATED — no fresh real option contract. Actual fill logging is unavailable from this alert.'}
  from core.fill_flow import begin
  flow_message=begin(s,signal,now=now)
  s.put('paper_fill_prompt:owner',{'signal_id':id,'contract':c['symbol'],'signal_timestamp':signal['timestamp'],'expires_at':signal['signal_expiry']})
  return {'text':flow_message+'\nPAPER / UNVALIDATED — report YOUR actual fill, never the suggested price:\n/option_bought '+c['symbol']+' CONTRACTS ACTUAL_PREMIUM TOTAL_FEES ACTUAL_FILL_TIME_WITH_OFFSET\nThe next matching report before signal expiry is linked to this signal. No order is submitted.'}
 finally:
  if own:s.close()
if __name__=='__main__':
 try:print(json.dumps(execute(json.load(sys.stdin))))
 except (ValueError,KeyError,TypeError):print(json.dumps({'text':'PAPER / UNVALIDATED — action refused: owner authorization, signal or expiry validation failed. No order.'}))
