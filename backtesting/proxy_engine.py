"""SPY-share proxy evidence, isolated from real holdings and option paper records."""
import hashlib,json,math,random,statistics
from datetime import datetime,timezone,timedelta
from core.storage import Store,encode
from core.sessions import ET,market_session
from core.signals import Signal,tier,finalize,quote_valid
from data.models import stamp,finite
from features.indicators import normalize,calculate
MODE='UNDERLYING_PROXY_ONLY'
def critical_t(sample_size):
    """NIST .975 quantiles, conservatively padded for table rounding; df>30 uses df30."""
    # https://www.itl.nist.gov/div898/handbook/eda/section3/eda3672.htm
    values=(12.706,4.303,3.182,2.776,2.571,2.447,2.365,2.306,2.262,2.228,2.201,2.179,2.160,2.145,2.131,2.120,2.110,2.101,2.093,2.086,2.080,2.074,2.069,2.064,2.060,2.056,2.052,2.048,2.045,2.042)
    if type(sample_size) is not int or sample_size<2:raise ValueError('T_INTERVAL_REQUIRES_TWO_SAMPLES')
    return values[min(sample_size-2,29)]+.001
def candidate(store,news,config,now):
    from research.live_trend import evaluate
    live=evaluate(store,now);feed=live.get('feed');provider=live.get('provider','UNAVAILABLE')
    q=store.get('quote:SPY' if feed=='sip' else 'research_quote:SPY:iex',{})
    rows=store.get('stream_bars:SPY' if feed=='sip' else 'research_stream_bars:SPY:iex',[])
    sid=hashlib.sha256(json.dumps([MODE,provider,live.get('bar_end'), 'proxy-opening-v1']).encode()).hexdigest()[:24]
    s=Signal(sid,now.isoformat(),q.get('source_timestamp'),provider,paper_mode=MODE,feed_quality=(feed or 'UNAVAILABLE').upper(),strategy_version='proxy-opening-v1',scoring_version='proxy-evidence-v1',news_status=news['risk'])
    s.signal_expiry=(now+timedelta(seconds=config.get('signal_expiry_seconds',600))).isoformat();s.max_holding_minutes=config.get('proxy_paper',{}).get('max_holding_minutes',60)
    reasons=[];session=market_session(now)
    from options.trade_plan import mismatch
    if mismatch([store.get('quote:SPY',{}) or {},store.get('research_quote:SPY:iex',{}) or {}],config,now):reasons.append('FEED_MISMATCH')
    clock=store.get('ntp_clock',{}) or {}
    if clock.get('state')=='MEASURED' and abs(clock.get('offset_seconds',0))>config.get('max_future_skew_seconds',2):reasons.append('CLOCK_OFFSET_BEYOND_TOLERANCE')
    if live['status']!='LIVE_TREND' or not quote_valid(q,now):reasons.append('PROXY_FRESH_FEED_AND_31_BAR_TAIL_REQUIRED')
    if not session['active'] or now.astimezone(ET).hour*60+now.astimezone(ET).minute>=session['close_minute']-5:reasons.append('OUTSIDE_PROXY_ENTRY_SESSION')
    if news['quality']!='DATA_OK' or news['risk'] not in ('NORMAL','MODERATE'):reasons.append('NEWS_UNAVAILABLE_OR_BLACKOUT')
    try:
        bars=normalize(rows,now=now);bars=[b for b in bars if datetime.fromtimestamp(b['timestamp'],timezone.utc).astimezone(ET).date()==now.astimezone(ET).date()];f=calculate(bars)
        first=bars[:15];opening={'high':max(b['high'] for b in first),'low':min(b['low'] for b in first)} if len(first)==15 and first[0]['timestamp']==datetime.combine(now.astimezone(ET).date(),datetime.min.time(),ET).timestamp()+570*60 else None
        px=q.get('payload',{}).get('mid');s.spy_price=px;s.vwap=f.get('vwap_approx');s.volatility_status='OBSERVED';s.market_regime='BULL' if live.get('direction')=='UP' else 'BEAR' if live.get('direction')=='DOWN' else 'NEUTRAL'
        sign=1 if live.get('direction')=='UP' else -1 if live.get('direction')=='DOWN' else 0
        if not opening or not sign or not finite(px) or not finite(s.vwap):reasons.append('PROXY_SETUP_INPUTS_UNAVAILABLE')
        else:
            boundary=opening['high' if sign==1 else 'low'];setup='OPENING_RANGE_BREAKOUT'
            if (bars[-1]['close']-boundary)*sign<=0:
                reclaim=bars[-2]['close']<=f['previous_vwap_approx'] and bars[-1]['close']>s.vwap if sign==1 else bars[-2]['close']>=f['previous_vwap_approx'] and bars[-1]['close']<s.vwap
                if reclaim:
                    boundary=min(bars[-2]['low'],bars[-1]['low']) if sign==1 else max(bars[-2]['high'],bars[-1]['high']);setup='VWAP_RECLAIM' if sign==1 else 'VWAP_REJECTION';s.strategy_version='proxy-vwap-v1'
            recent=statistics.mean(b['volume'] for b in bars[-11:-1]) if len(bars)>=11 else 0
            confirmations={'completed_breakout':(bars[-1]['close']-boundary)*sign>0,'quote_beyond_boundary':(px-boundary)*sign>0,'vwap_alignment':(px-s.vwap)*sign>0,'recent_volume':recent>0 and bars[-1]['volume']>=1.2*recent,'local_structure':bars[-1]['low']>bars[-2]['low'] if sign==1 else bars[-1]['high']<bars[-2]['high']}
            s.score=20*sum(confirmations.values());s.tier=tier(s.score);s.multi_timeframe_alignment={'basis':'31 completed current-session 1m bars; not options MTF readiness',**live.get('votes',{})}
            s.direction='CALL' if sign==1 else 'PUT';s.setup_type=setup;s.entry_condition='Completed '+setup.lower().replace('_',' ')+'; all five proxy confirmations';s.invalidation=boundary;s.underlying_entry_range=[q['payload']['bid'],q['payload']['ask']];distance=abs(px-boundary)
            if not .02<distance<=config.get('proxy_paper',{}).get('max_risk_per_share_usd',5):reasons.append('PROXY_RISK_DISTANCE_OUTSIDE_LIMIT')
            else:s.t1=px+sign*1.5*distance;s.t2=px+sign*2*distance;s.risk_reward=2
            if setup!='OPENING_RANGE_BREAKOUT':
                from features.indicators import resample
                opposing='BEAR' if sign==1 else 'BULL'
                if any(calculate(resample(bars,n)).get('trend')==opposing for n in (15,30,60)):reasons.append('PROXY_HIGHER_FRAME_CONTRADICTS')
            if not all(confirmations.values()):reasons.append('PROXY_CONFIRMATION_MISSING')
            s.explanation=['Five correlated binary checks, not probabilities. Recent-volume comparison is not historical same-slot RVOL.']
    except (ValueError,KeyError,TypeError,IndexError):reasons.append('PROXY_BARS_INVALID')
    s.signal_id=hashlib.sha256((sid+s.strategy_version+s.setup_type).encode()).hexdigest()[:24]
    finalize(s,reasons,config);return s,q,rows
class ProxyEngine:
    def __init__(self,path):
        self.store=Store(path);self.db=self.store.db
        for table in ('proxy_events','proxy_baseline_events'):
            self.db.executescript(f'''CREATE TABLE IF NOT EXISTS {table}(id TEXT PRIMARY KEY,payload TEXT NOT NULL,created TEXT NOT NULL);
            CREATE TRIGGER IF NOT EXISTS {table}_no_update BEFORE UPDATE ON {table} BEGIN SELECT RAISE(ABORT,'append only'); END;
            CREATE TRIGGER IF NOT EXISTS {table}_no_delete BEFORE DELETE ON {table} BEGIN SELECT RAISE(ABORT,'append only'); END;''')
    def close(self):self.store.close()
    def positions(self,baseline=False):
        table='proxy_baseline_events' if baseline else 'proxy_events';positions={}
        for r in self.db.execute(f'SELECT payload FROM {table} ORDER BY rowid'):
            e=json.loads(r[0]);positions[e['signal_id']]=e
        return list(positions.values())
    def append(self,p,suffix,baseline=False):
        from core.isolation import assert_real
        assert_real(p)
        table='proxy_baseline_events' if baseline else 'proxy_events'
        with self.db:self.db.execute(f'INSERT OR IGNORE INTO {table} VALUES(?,?,?)',(p['signal_id']+suffix,encode(p),p.get('closed_at',p.get('last_bar_end',p['opened_at']))))
    def risk_state(self,now):
        closed=[p for p in self.positions() if p['status']=='CLOSED'];day=now.astimezone(ET).date();streak=0
        for p in reversed(sorted(closed,key=lambda p:stamp(p['closed_at']))):
            if p['pnl_usd']>=0:break
            streak+=1
        return {'daily_loss_usd':sum(-p['pnl_usd'] for p in closed if p['pnl_usd']<0 and stamp(p['closed_at']).astimezone(ET).date()==day),'consecutive_losses':streak,'daily_reconciled_date':day.isoformat(),'basis':MODE}
    def open(self,signal,q,config,now):
        s=signal.dict() if hasattr(signal,'dict') else signal;settings=config['proxy_paper'];session=market_session(now)
        if not settings['enabled'] or not config.get('allow_unvalidated_paper_trading') or not s.get('paper_eligible') or s.get('paper_mode')!=MODE:raise ValueError('PROXY_NOT_ELIGIBLE')
        if s.get('feed_quality') not in ('IEX','SIP') or q.get('provider')!='alpaca-'+s['feed_quality'].lower() or not quote_valid(q,now):raise ValueError('PROXY_QUOTE_NOT_VERIFIED')
        if not session['active'] or now.astimezone(ET).hour*60+now.astimezone(ET).minute>=session['close_minute']-5:raise ValueError('PROXY_ENTRY_SESSION_CLOSED')
        if stamp(s['signal_expiry'])<=now:raise ValueError('SIGNAL_EXPIRED')
        if any(p['signal_id']==s['signal_id'] for p in self.positions()):return 'ALREADY_RECORDED'
        state=self.risk_state(now);limits=config['options_risk']
        if state['daily_loss_usd']>=limits['max_daily_loss_usd'] or state['consecutive_losses']>=limits['max_consecutive_losses']:raise ValueError('PROXY_LOSS_LIMIT')
        if sum(p['status']=='OPEN' for p in self.positions())>=settings['max_open_positions']:raise ValueError('PROXY_OPEN_POSITION_LIMIT')
        sign=1 if s['direction']=='CALL' else -1 if s['direction']=='PUT' else 0;slip=settings['slippage_per_share'];fill=q['payload']['ask']+slip if sign==1 else q['payload']['bid']-slip
        risk=(fill-s['invalidation'])*sign
        if not sign or not 0<risk<=settings['max_risk_per_share_usd'] or (s['t2']-fill)*sign<=0:raise ValueError('PROXY_LEVELS_INVALID')
        p={'signal_id':s['signal_id'],'mode':MODE,'status':'OPEN','direction':'LONG' if sign==1 else 'SHORT','sign':sign,'entry':fill,'invalidation':s['invalidation'],'t1':s['t1'],'t2':s['t2'],'quantity':settings['quantity'],'slippage':slip,'spread':q['payload']['ask']-q['payload']['bid'],'cost_model':'Entry observed bid/ask; exit completed-bar trigger adjusted by entry spread/2 and slippage (model, not an observed exit quote).','opened_at':now.astimezone(timezone.utc).isoformat(),'max_holding_minutes':settings['max_holding_minutes'],'risk_per_share':risk,'mfe_usd_per_share':0.,'mae_usd_per_share':0.,'setup':s['setup_type'],'regime':s['market_regime'],'score':s['score'],'feed_quality':s['feed_quality'],'provider':q['provider'],'signal':s}
        self.append(p,'-entry')
        # Matched-clock random direction benchmark; deterministic seed, no optimized outcome.
        b=dict(p);b['signal_id']=p['signal_id']+'-baseline';bsign=random.Random(int(hashlib.sha256(s['signal_id'].encode()).hexdigest(),16)).choice((-1,1));mid=q['payload']['mid'];b['sign']=bsign;b['direction']='LONG' if bsign==1 else 'SHORT';b['entry']=q['payload']['ask']+slip if bsign==1 else q['payload']['bid']-slip;b['invalidation']=mid-bsign*abs(mid-p['invalidation']);b['t1']=mid+bsign*abs(mid-p['t1']);b['t2']=mid+bsign*abs(mid-p['t2']);b['risk_per_share']=(b['entry']-b['invalidation'])*bsign;self.append(b,'-entry',True)
        return p
    def mark(self,rows,news,now,feed_quality=None):
        changes=[]
        for baseline in (False,True):
            for p in self.positions(baseline):
                if p['status']!='OPEN':continue
                if feed_quality is not None and p['feed_quality']!=feed_quality:continue
                bars=normalize(rows,now=now)
                for b in bars:
                    start=datetime.fromtimestamp(b['timestamp'],timezone.utc);end=start+timedelta(minutes=1)
                    if start<stamp(p['opened_at']) or end<=stamp(p.get('last_bar_end',p['opened_at'])):continue
                    if start.astimezone(ET).date()!=stamp(p['opened_at']).astimezone(ET).date():continue
                    expected=stamp(p.get('last_bar_end',p['opened_at']))
                    if 'last_bar_end' not in p:expected=datetime.fromtimestamp(math.ceil(expected.timestamp()/60)*60,timezone.utc)
                    if start>expected:
                        first_gap=not p.get('coverage_incomplete');p.update(coverage_incomplete=True,update_reason='DATA_GAP_POSITION_UNRESOLVED',missing_bar_from=expected.isoformat(),observed_next_bar=start.isoformat())
                        self.append(p,'-gap-'+start.isoformat(),baseline)
                        if not baseline and first_gap:changes.append(dict(p))
                        # Do not infer missed stops, fills or complete excursions. Backfill may resolve this later.
                        break
                    p['coverage_incomplete']=False;p.pop('update_reason',None)
                    sign=p['sign'];fav=(b['high']-p['entry']) if sign==1 else p['entry']-b['low'];adv=(b['low']-p['entry']) if sign==1 else p['entry']-b['high'];p['mfe_usd_per_share']=max(p['mfe_usd_per_share'],fav);p['mae_usd_per_share']=min(p['mae_usd_per_share'],adv)
                    stop=b['low']<=p['invalidation'] if sign==1 else b['high']>=p['invalidation'];target=b['high']>=p['t2'] if sign==1 else b['low']<=p['t2'];t1=b['high']>=p['t1'] if sign==1 else b['low']<=p['t1'];reason=None;price=b['close']
                    if stop:reason='STOP_INVALIDATION';price=min(b['open'],p['invalidation']) if sign==1 else max(b['open'],p['invalidation'])
                    elif target:reason='T2_REACHED';price=p['t2']
                    elif news.get('risk')=='HIGH' and 0<=(now-end).total_seconds()<=120:reason='NEWS_BLACKOUT'
                    elif news.get('quality')!='DATA_OK' and 0<=(now-end).total_seconds()<=120:reason='ABNORMAL_NEWS_DATA'
                    elif end.astimezone(ET).hour*60+end.astimezone(ET).minute>=market_session(start)['close_minute']-5:reason='FORCED_FLAT'
                    elif (end-stamp(p['opened_at'])).total_seconds()>=p['max_holding_minutes']*60:reason='TIME_STOP'
                    p['last_bar_end']=end.isoformat()
                    if reason:
                        fill=price-sign*(p['spread']/2+p['slippage']);net=(fill-p['entry'])*sign;p.update(status='CLOSED',exit=fill,exit_reason=reason,pnl_usd_per_share=net,pnl_usd=net*p['quantity'],r_multiple=net/p['risk_per_share'],closed_at=end.isoformat(),holding_seconds=(end-stamp(p['opened_at'])).total_seconds())
                    new_t1=t1 and not p.get('t1_reached')
                    if new_t1:p['t1_reached']=True
                    self.append(p,'-'+end.isoformat(),baseline)
                    if not baseline and (reason or new_t1):changes.append(dict(p))
                    if reason:break
        return changes
    def summary(self):
        def stats(rows):
            vals=[p['pnl_usd_per_share'] for p in rows if p['status']=='CLOSED'];n=len(vals);mean=statistics.mean(vals) if vals else None;ci=None
            if n>=2:
                # Student-t conservative small sample interval; dependent trade caveat shown.
                critical=critical_t(n)
                margin=critical*statistics.stdev(vals)/math.sqrt(n);ci=[mean-margin,mean+margin]
            return {'closed':n,'open':sum(p['status']=='OPEN' for p in rows),'mean_usd_per_share':mean,'mean_95pct_ci':ci}
        rows=self.positions();setups={p.get('setup','UNAVAILABLE') for p in rows}
        return {'by_setup':{k:stats([p for p in rows if p.get('setup','UNAVAILABLE')==k]) for k in sorted(setups)},'metric':'UNDERLYING_PROXY_EVIDENCE','proxy':stats(rows),'matched_clock_random_direction_baseline':stats(self.positions(True)),'limitations':'Unvalidated share proxy, not option P&L or readiness. CI assumes independent trade samples; trades may be correlated. Baseline uses same times/distances/cost model.'}
