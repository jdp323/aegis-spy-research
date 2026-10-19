"""Separate append-only theoretical ledger. Ask entries/bid exits with costs."""
from decimal import Decimal
from datetime import datetime,timezone
from data.models import stamp
from core.storage import Store
D=lambda x:Decimal(str(x))
class PaperEngine:
    def __init__(self,path,kind='paper'):
        if kind not in ('paper','paper_baseline'):raise ValueError('INVALID_PAPER_NAMESPACE')
        self.kind=kind;self.store=Store(path)
    def positions(self):
        positions={}
        for e in reversed(self.store.events(self.kind,100000)):
            p=positions.setdefault(e['signal_id'],{})
            p.update(e)
        return list(positions.values())
    def risk_state(self,now=None):
        """Reconcile only non-synthetic option paper records on the current ET date."""
        from core.sessions import ET
        now=now or datetime.now(timezone.utc)
        if now.tzinfo is None or now.utcoffset() is None:raise ValueError('AWARE_CLOCK_REQUIRED')
        day=now.astimezone(ET).date().isoformat()
        rows=[p for p in self.positions() if not p.get('synthetic')]
        closed=sorted((p for p in rows if p['status']=='CLOSED'),key=lambda p:stamp(p['closed_at']))
        if any(stamp(p['closed_at'])>now for p in closed):raise ValueError('FUTURE_PAPER_OUTCOME')
        loss=sum(-D(p['pnl_usd']) for p in closed if D(p['pnl_usd'])<0 and stamp(p['closed_at']).astimezone(ET).date().isoformat()==day)
        streak=0
        for p in reversed(closed):
            if D(p['pnl_usd'])>=0:break
            streak+=1
        positions=[{'quantity':p['quantity'],'cost_usd':p['entry_cost']} for p in rows if p['status']=='OPEN']
        return {'daily_loss_usd':float(loss),'consecutive_losses':streak,'daily_reconciled_date':day,'positions':positions,'basis':'OPTION_PAPER_LEDGER_ONLY','reconciled_at':now.astimezone(timezone.utc).isoformat()}
    def open(self,signal,quote,quantity=1,slippage='0.01',fee='0.65',now=None,synthetic=False):
        now=now or datetime.now(timezone.utc);s=signal.dict() if hasattr(signal,'dict') else signal
        from core.isolation import assert_real
        assert_real(s);assert_real(quote)
        if any(p['signal_id']==s['signal_id'] for p in self.positions()):return 'ALREADY_RECORDED'
        blockers=[r for r in s.get('rejection_reasons',[]) if r!='STRATEGY_PROSPECTIVE_VALIDATION_MISSING']
        if not synthetic and (not s.get('paper_eligible') or s.get('paper_mode')!='OPTIONS_REAL_QUOTES'):raise ValueError('PAPER_ROUTING_NOT_AUTHORIZED')
        if not synthetic:
            from core.signals import option_quote_valid
            if not option_quote_valid(quote,now):raise ValueError('REAL_OPTION_QUOTE_REQUIRED')
        if blockers or not s.get('option_contract') or (s.get('score') or 0)<75:raise ValueError('PAPER_SIGNAL_REJECTED')
        self.valid_quote(quote,now)
        if quote.get('symbol')!=s['option_contract']['symbol']:raise ValueError('WRONG_CONTRACT_QUOTE')
        if type(quantity) is not int or quantity<=0 or D(slippage)<0 or D(fee)<0:raise ValueError('INVALID_PAPER_COSTS')
        if stamp(s['signal_expiry'])<=now:raise ValueError('SIGNAL_EXPIRED')
        fill=D(quote['payload']['ask'])+D(slippage);cost=fill*100*quantity+D(fee)*quantity
        e={'signal_id':s['signal_id'],'status':'OPEN','contract':s['option_contract']['symbol'],'quantity':quantity,'theoretical_entry':str(quote['payload']['mid']),'entry':str(fill),'entry_cost':str(cost),'spread':quote['payload']['ask']-quote['payload']['bid'],'slippage':slippage,'entry_fee':str(D(fee)*quantity),'opened_at':now.isoformat(),'mfe_usd':'0','mae_usd':'0','signal':s,'synthetic':synthetic,'setup':s['setup_type'],'regime':s['market_regime'],'timeframe':'5m','delta':s['option_contract'].get('delta'),'expiry':s['option_contract'].get('expiry'),'score':s['score'],'horizon':s.get('horizon','UNAVAILABLE'),'mode':'OPTIONS_REAL_QUOTES'}
        self.store.event(self.kind+'-entry-'+s['signal_id'],self.kind,e);return e
    @staticmethod
    def valid_quote(q,now):
        from core.isolation import assert_real
        assert_real(q)
        if q.get('quality')!='DATA_OK' or not q.get('source_timestamp') or not 0<q['payload']['bid']<=q['payload']['ask'] or not 0<=(now-stamp(q['source_timestamp'])).total_seconds()<=15:raise ValueError('PAPER_QUOTE_INVALID')
    def mark(self,id,quote,exit_reason=None,slippage='0.01',fee='0.65',now=None):
        now=now or datetime.now(timezone.utc);self.valid_quote(quote,now);p=next(p for p in self.positions() if p['signal_id']==id)
        if not p.get('synthetic'):
            from core.signals import option_quote_valid
            if not option_quote_valid(quote,now):raise ValueError('REAL_OPTION_QUOTE_REQUIRED')
        if quote.get('symbol')!=p['contract']:raise ValueError('WRONG_CONTRACT_QUOTE')
        if p['status']!='OPEN':return p
        if stamp(quote['source_timestamp'])<stamp(p['opened_at']):raise ValueError('LOOKAHEAD_OR_OLD_QUOTE')
        fill=max(D(0),D(quote['payload']['bid'])-D(slippage));net=fill*100*p['quantity']-D(fee)*p['quantity']-D(p['entry_cost'])
        p.update(mark=str(fill),estimated_net_usd=str(net),mfe_usd=str(max(D(p['mfe_usd']),net)),mae_usd=str(min(D(p['mae_usd']),net)),last_mark_at=now.isoformat())
        if exit_reason:p.update(status='CLOSED',exit_reason=exit_reason,exit=str(fill),pnl_usd=str(net),exit_fee=str(D(fee)*p['quantity']),closed_at=now.isoformat(),holding_seconds=(now-stamp(p['opened_at'])).total_seconds())
        self.store.event(self.kind+'-'+id+'-'+str(quote['source_timestamp'])+('-exit' if exit_reason else ''),self.kind,p);return p
