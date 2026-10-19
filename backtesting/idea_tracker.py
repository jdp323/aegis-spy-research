"""Independent append-only SPY ideas. Underlying outcomes are never option P&L."""
import sqlite3,json,math,statistics
from datetime import timedelta,timezone
from data.models import stamp,finite
from core.sessions import ET,market_session
from core.isolation import assert_real
from core.idea_config import settings
from backtesting.proxy_engine import critical_t
def evidence(rows):
    closed=[r for r in rows if r.get('status')=='CLOSED' and finite(r.get('r_multiple'))]
    values=[r['r_multiple'] for r in closed];n=len(values);mean=statistics.mean(values) if n else None
    margin=critical_t(n)*statistics.stdev(values)/math.sqrt(n) if n>=2 else None
    interval=[mean-margin,mean+margin] if margin is not None else None
    tag='INSUFFICIENT DATA' if n<50 else 'POSITIVE' if interval[0]>0 else 'NEGATIVE' if interval[1]<0 else 'UNCLEAR'
    return {'closed':n,'total':len(rows),'expired_no_entry':sum(r.get('status')=='EXPIRED_NO_ENTRY' for r in rows),'t1_hits':sum(bool(r.get('t1_hit')) for r in closed),'t2_hits':sum(r.get('exit_reason')=='TARGET_2_HIT' for r in closed),'t1_hit_rate':sum(bool(r.get('t1_hit')) for r in closed)/n if n else None,'t2_hit_rate':sum(r.get('exit_reason')=='TARGET_2_HIT' for r in closed)/n if n else None,'average_r':mean,'expectancy_ci95':interval,'evidence_tag':tag,'basis':'UNDERLYING (not option P&L)','caution':'Heuristic interval on correlated sampled ideas; not strategy validation.'}
class IdeaTracker:
    def __init__(self,path=None,simulation=False,baseline=False):
        if simulation and path is not None:raise ValueError('SIMULATION_MEMORY_ONLY')
        self.simulation=simulation;self.memory=[];self.db=None;self.baseline=baseline;self.path=path;self.shadow=None
        self.table="idea_baseline_events" if baseline else "idea_events"
        if not simulation:
            from pathlib import Path
            path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
            self.db=sqlite3.connect(path,timeout=15)
            self.db.executescript(f'''PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS {self.table}(id TEXT PRIMARY KEY,signal_id TEXT NOT NULL,event_type TEXT NOT NULL,payload TEXT NOT NULL,created TEXT NOT NULL);
            CREATE TRIGGER IF NOT EXISTS {self.table}_no_update BEFORE UPDATE ON {self.table} BEGIN SELECT RAISE(ABORT,'append only'); END;
            CREATE TRIGGER IF NOT EXISTS {self.table}_no_delete BEFORE DELETE ON {self.table} BEGIN SELECT RAISE(ABORT,'append only'); END;''')
    def close(self):
        if getattr(self,'shadow',None):self.shadow.close()
        if self.db:self.db.close()
    def append(self,p,kind,now):
        if now.tzinfo is None:raise ValueError('AWARE_UTC_TIME_REQUIRED')
        now=now.astimezone(timezone.utc);p=dict(p)
        for name in ('timestamp','market_timestamp','signal_expiry','max_hold_until','opened_at','closed_at','last_bar_end'):
            if p.get(name):p[name]=stamp(p[name]).astimezone(timezone.utc).isoformat()
        if not self.simulation:assert_real(p)
        elif p.get('feed_quality')!='SIMULATED':raise ValueError('SIMULATION_REQUIRES_TAG')
        key=p['signal_id']+':'+kind+':'+now.isoformat()
        if self.db:
            with self.db:self.db.execute('INSERT OR IGNORE INTO '+self.table+' VALUES(?,?,?,?,?)',(key,p['signal_id'],kind,json.dumps(p,allow_nan=False),now.isoformat()))
        else:
            if not any(x[0]==key for x in self.memory):self.memory.append((key,dict(p)))
    def positions(self):
        result={}
        rows=(json.loads(r[0]) for r in self.db.execute('SELECT payload FROM '+getattr(self,'table','idea_events')+' ORDER BY rowid')) if self.db else (x[1] for x in self.memory)
        for row in rows:
            if not self.simulation:assert_real(row)
            result[row['signal_id']]=row
        return list(result.values())
    def register(self,idea,quote,now,alerted=False):
        from core.signals import quote_valid
        if now.tzinfo is None:raise ValueError('AWARE_UTC_TIME_REQUIRED')
        if now>=stamp(idea['max_hold_until']) or now>=stamp(idea['signal_expiry']):raise ValueError('ENTRY_DEADLINE_PASSED')
        if stamp(idea['signal_expiry'])>stamp(idea['max_hold_until']):raise ValueError('ENTRY_VALIDITY_EXCEEDS_HOLDING_DEADLINE')
        if not self.simulation and (not quote_valid(quote,now,5) or idea.get('feed_quality') not in ('SIP','IEX')):raise ValueError('IDEA_QUOTE_NOT_VERIFIED')
        if self.simulation and quote.get('feed_quality')!='SIMULATED':raise ValueError('SIMULATION_REQUIRES_TAG')
        if any(x['signal_id']==idea['signal_id'] for x in self.positions()):return None
        p=dict(idea,entry_spread=quote['payload']['ask']-quote['payload']['bid'],cost_version='spread-half-plus-slip-v2',coverage_status='COMPLETE_SO_FAR',status='PENDING',alerted=alerted,mfe=0.,mae=0.,t1_hit=False,last_bar_end=None)
        if idea['entry_mode']=='ENTER NOW':
            sign=1 if idea['direction']=='CALL' else -1
            fill=quote['payload']['ask' if sign==1 else 'bid']+sign*.01
            p.update(status='OPEN',opened_at=now.isoformat(),fill_price=fill,modeled_entry_fill=fill)
        self.append(p,'REGISTER',now)
        if not self.baseline:
            import hashlib
            if self.shadow is None:self.shadow=IdeaTracker(self.path,self.simulation,baseline=True)
            # Matched entry clock, costs and absolute stop/target/holding distances;
            # direction is deterministic random assignment, never chosen by outcome.
            sign=1 if hashlib.sha256(('baseline-v6:'+idea['signal_id']).encode()).digest()[0]<128 else -1
            reference=quote['payload']['mid'];shadow=dict(idea,signal_id=idea['signal_id']+'-baseline',paired_signal_id=idea['signal_id'],direction='CALL' if sign==1 else 'PUT',entry_mode='ENTER NOW',entry=reference,trigger=reference,invalidation=reference-sign*abs(idea['entry']-idea['invalidation']),t1=reference+sign*abs(idea['t1']-idea['entry']),t2=reference+sign*abs(idea['t2']-idea['entry']),population='MATCHED_CLOCK_RANDOM_DIRECTION')
            self.shadow.register(shadow,quote,now,False)
        return p
    def observe(self,bars,now,news=None,feed_quality=None):
        if not self.simulation:assert_real(bars)
        changes=[]
        for p in self.positions():
            if p['status'] not in ('OPEN','PENDING'):continue
            before=json.dumps(p,sort_keys=True)
            sign=1 if p['direction']=='CALL' else -1
            for b in bars:
                if feed_quality and feed_quality!=p['feed_quality']:continue
                end=stamp(b['t'])+timedelta(minutes=1)
                if end>now or stamp(b['t'])<stamp(p.get('opened_at',p['timestamp'])) or p.get('last_bar_end') and end<=stamp(p['last_bar_end']):continue
                if not all(finite(b.get(k)) for k in ('o','h','l','c')) or not 0<b['l']<=min(b['o'],b['c'])<=max(b['o'],b['c'])<=b['h']:raise ValueError('INVALID_OUTCOME_BAR')
                if not self.simulation and (b.get('feed_quality')=='SIMULATED' or p['feed_quality'] not in ('SIP','IEX')):raise ValueError('INVALID_OUTCOME_FEED')
                expected=stamp(p['last_bar_end']) if p.get('last_bar_end') else stamp(p.get('opened_at',p['timestamp'])).replace(second=0,microsecond=0)+timedelta(minutes=bool(stamp(p.get('opened_at',p['timestamp'])).second or stamp(p.get('opened_at',p['timestamp'])).microsecond))
                if stamp(b['t'])>expected:
                    p.update(coverage_status='UNRESOLVED_GAP',missing_from=expected.isoformat());break
                if p.get('coverage_status')=='UNRESOLVED_GAP':p.update(coverage_status='COMPLETE_SO_FAR',missing_from=None)
                if p['status']=='PENDING':
                    if min(stamp(p['signal_expiry']),stamp(p['max_hold_until']))<=stamp(b['t']):break
                    if (b['l']<=p['invalidation'] if sign==1 else b['h']>=p['invalidation']):p.update(status='CANCELLED',closed_at=end.isoformat(),exit_reason='IDEA_CANCELLED');break
                    if not (b['h']>=p['trigger'] if sign==1 else b['l']<=p['trigger']):continue
                    p.update(status='OPEN',opened_at=end.isoformat(),fill_price=(max(b['o'],p['trigger']) if sign==1 else min(b['o'],p['trigger']))+sign*.01)
                    changes.append((dict(p),'ENTRY_TRIGGERED'))
                entry=p['fill_price'];p['mfe']=max(p['mfe'],(b['h']-entry)*sign if sign==1 else (b['l']-entry)*sign);p['mae']=max(p['mae'],(entry-b['l'])*sign if sign==1 else (entry-b['h'])*sign)
                p['last_bar_end']=end.isoformat();stop=b['l']<=p['invalidation'] if sign==1 else b['h']>=p['invalidation'];t2=b['h']>=p['t2'] if sign==1 else b['l']<=p['t2'];t1=b['h']>=p['t1'] if sign==1 else b['l']<=p['t1']
                reason=None;exit_px=None
                if stop:reason='STOP_HIT';exit_px=min(b['o'],p['invalidation']) if sign==1 else max(b['o'],p['invalidation'])
                elif t2:reason='TARGET_2_HIT';exit_px=p['t2'];p['t1_hit']=True
                elif t1 and not p['t1_hit']:p['t1_hit']=True;changes.append((dict(p),'TARGET_1_HIT'))
                session=market_session(end);minute=end.astimezone(ET).hour*60+end.astimezone(ET).minute
                if not reason and (end>=stamp(p['max_hold_until']) or minute>=session['close_minute']-5):reason='TIME_EXIT';exit_px=b['c']
                if reason:
                    exit_px-=sign*(.01+p.get('entry_spread',0)/2);p.update(status='CLOSED',closed_at=end.isoformat(),exit_reason=reason,exit_price=exit_px,usd_per_share=(exit_px-entry)*sign,r_multiple=(exit_px-entry)*sign/abs(entry-p['invalidation']),holding_seconds=(end-stamp(p['opened_at'])).total_seconds())
                    break
            if p['status']=='PENDING' and now>=stamp(p['signal_expiry']):p.update(status='EXPIRED_NO_ENTRY',closed_at=now.isoformat(),exit_reason='IDEA_EXPIRED')
            # No stale quote or bar is invented for a time/news exit: wait for genuine bar evidence.
            if p['status']=='OPEN' and news and news.get('risk')=='HIGH':
                changes.append((dict(p),'NEWS_EXIT_REVIEW'))
            if json.dumps(p,sort_keys=True)!=before:self.append(p,'OBSERVE',now)
            if p['status'] not in ('OPEN','PENDING'):changes.append((dict(p),p['exit_reason']))
        if not getattr(self,'baseline',False):
            shadow=getattr(self,'shadow',None)
            if shadow is None and self.db:
                shadow=self.shadow=IdeaTracker(self.path,baseline=True)
            if shadow:shadow.observe(bars,now,news,feed_quality)
        return changes
    def summary(self,now):
        rows=self.positions();day=now.astimezone(ET).date()
        result={'basis':'UNDERLYING (not option P&L)','all':evidence(rows),'windows':{},'setups':{}}
        for label,days in [('today',1),('7_days',7),('30_days',30)]:result['windows'][label]=evidence([r for r in rows if 0<=(day-stamp(r['timestamp']).astimezone(ET).date()).days<days])
        for key in sorted({(r['setup_type'],bool(r.get('early'))) for r in rows}):result['setups'][key[0]+('-early' if key[1] else '')]=evidence([r for r in rows if (r['setup_type'],bool(r.get('early')))==key])
        if not getattr(self,'baseline',False):
            shadow=getattr(self,'shadow',None)
            if shadow is None and self.db:
                # Read-only packet inspection must never create a missing table.
                present=self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='idea_baseline_events'").fetchone()
                if present:
                    shadow=IdeaTracker.__new__(IdeaTracker);shadow.db=self.db;shadow.memory=[];shadow.simulation=False;shadow.baseline=True;shadow.table='idea_baseline_events'
            baseline=shadow.positions() if shadow else []
            result['random_direction_baseline']=evidence(baseline)
            matched={x.get('paired_signal_id'):x for x in baseline if x.get('status')=='CLOSED' and finite(x.get('r_multiple'))}
            pairs=[r['r_multiple']-matched[r['signal_id']]['r_multiple'] for r in rows if r.get('status')=='CLOSED' and finite(r.get('r_multiple')) and r['signal_id'] in matched]
            mean=statistics.mean(pairs) if pairs else None;margin=critical_t(len(pairs))*statistics.stdev(pairs)/math.sqrt(len(pairs)) if len(pairs)>1 else None
            result['paired_baseline_comparison']={'closed_pairs':len(pairs),'mean_difference_r':mean,'ci95':[mean-margin,mean+margin] if margin is not None else None,'interpretation':'Matched clock, directions randomized; intervals are heuristic and overlapping outcomes are correlated. Not strategy validation.'}
        return result
def score_text(summary):
    lines=['SPY SCORE — UNDERLYING (not option P&L)','Population: V5/V6 ideas only; separate from proxy trades, real-quote option paper and forward diagnostics.','Evidence labels require 50 closed ideas. Multiple setups are tested; some can look good or bad by chance.']
    for label,s in summary['windows'].items():lines.append(label+': '+str(s['closed'])+' closed, '+str(s['expired_no_entry'])+' expired without entry; T1 '+str(s['t1_hits'])+'/'+str(s['closed'])+' / T2 '+str(s['t2_hits'])+'/'+str(s['closed'])+'; average R '+('%.2f'%s['average_r'] if s['average_r'] is not None else 'UNAVAILABLE')+'; CI '+str(s['expectancy_ci95'])+'; '+s['evidence_tag'])
    for name,s in summary['setups'].items():lines.append(name+': '+str(s['closed'])+' closed; '+s['evidence_tag']+'; CI '+str(s['expectancy_ci95']))
    lines+=['Random-direction baseline (separate population): '+str(summary.get('random_direction_baseline',{}).get('closed',0))+' closed; paired comparison '+str(summary.get('paired_baseline_comparison',{}))]
    return '\n'.join(lines+['Small correlated samples are not proof of edge or option profits.'])[:3300]
