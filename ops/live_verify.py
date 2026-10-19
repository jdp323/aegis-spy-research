"""Minute-by-minute prospective live trend verification, never synthetic session results."""
import json,math,time,os
from datetime import datetime,timezone
from core.sessions import ET,market_session
from core.storage import ROOT,Store,encode
from data.models import stamp
from research.live_trend import evaluate,text_for
from urllib.parse import urlparse
def public_crosscheck(store,now,root=None):
 d=store.get('public_live_crosscheck') or {}
 if not d:
  from pathlib import Path
  if root is not None and Path(root).resolve()!=ROOT.resolve():return {'quality':'UNAVAILABLE','reason':'No public observation in this isolated data root.'}
  from data.trend_spy import refresh
  raw=refresh(now,max_age_seconds=300)
  bars=raw.get('bars',[])
  if raw.get('status')=='RESEARCH_DATA_RECEIVED' and bars:
   completed=[bar for bar in bars if isinstance(bar.get('timestamp'),(int,float)) and bar['timestamp']+300<=now.timestamp()]
   last=completed[-1] if completed else {};source=last.get('timestamp');price=last.get('close')
   if isinstance(source,(int,float)) and isinstance(price,(int,float)):
    d={'timestamp':datetime.fromtimestamp(source,timezone.utc).isoformat(),'price':price,'source_url':raw.get('source'),'fetched_at':raw.get('fetched_at')}

 try:
  from data.models import finite
  source=urlparse(d['source_url'])
  if source.scheme!='https' or source.hostname not in ('query1.finance.yahoo.com','query2.finance.yahoo.com','finance.yahoo.com') or not finite(d['price']) or d['price']<=0 or not 0<=(now-stamp(d['timestamp'])).total_seconds()<=600 or not 0<=(now-stamp(d['fetched_at'])).total_seconds()<=300:raise ValueError()
  return {**d,'quality':'PUBLIC_DELAY_UNVERIFIED','live_verified':False}
 except (ValueError,KeyError,TypeError):return {'quality':'UNAVAILABLE','reason':'No timestamped independent public observation; never inferred from IEX.'}
def sample(store,now=None,crosscheck=None,root=None):
 now=now or datetime.now(timezone.utc);session=market_session(now);et=now.astimezone(ET)
 if not session['active']:return {'state':'WAITING_FOR_REGULAR_SESSION','date':session['date']}
 key=et.strftime('%Y-%m-%d-%H-%M')
 if store.db.execute("SELECT name FROM sqlite_master WHERE name='live_verify_samples'").fetchone():
  old=store.db.execute('SELECT payload FROM live_verify_samples WHERE id=?',(key,)).fetchone()
  if old:return json.loads(old[0])
 before=time.perf_counter();live=evaluate(store,now);latency=(time.perf_counter()-before)*1000;data={'timestamp':now.isoformat(),'provider':live.get('provider','UNAVAILABLE'),'quote_age_seconds':live.get('quote_age_seconds'),'fresh_quote':live.get('quote_age_seconds') is not None and 0<=live['quote_age_seconds']<=5,'bar_tail_qualifies':live.get('status')=='LIVE_TREND','warmup_finished':et.hour*60+et.minute>=601,'analysis_latency_ms':latency,'trend':live.get('direction'),'trend_result':text_for(live,now),'public_crosscheck':crosscheck(store,now) if crosscheck else public_crosscheck(store,now,root)}
 store.db.execute('CREATE TABLE IF NOT EXISTS live_verify_samples(id TEXT PRIMARY KEY,et_date TEXT NOT NULL,payload TEXT NOT NULL)')
 with store.db:store.db.execute('INSERT OR IGNORE INTO live_verify_samples VALUES(?,?,?)',(et.strftime('%Y-%m-%d-%H-%M'),et.date().isoformat(),encode(data)))
 report(store,et.date().isoformat(),root=root);return data
def report(store,day,root=None):
 rows=[json.loads(r[0]) for r in store.db.execute('SELECT payload FROM live_verify_samples WHERE et_date=? ORDER BY id',(day,))];n=len(rows);warm=[r for r in rows if r['warmup_finished']];ages=sum(r['fresh_quote'] for r in rows)/n*100 if n else None;tails=sum(r['bar_tail_qualifies'] for r in rows)/n*100 if n else None;qualified=sum(r['bar_tail_qualifies'] for r in warm)/len(warm)*100 if warm else None;latencies=sorted(r['analysis_latency_ms'] for r in rows);p95=latencies[math.ceil(.95*n)-1] if n else None
 reasons=[]
 if n<30:reasons.append('Fewer than 30 real minute samples')
 if ages is None or ages<90:reasons.append('Fresh-quote rate below 90%')
 if len(warm)<10 or qualified is None or qualified<80:reasons.append('Post-warmup tail evidence insufficient/below 80%')
 if p95 is None or p95>2000:reasons.append('Analysis p95 unavailable/above 2000ms')
 checks=sum(r['public_crosscheck'].get('quality')!='UNAVAILABLE' for r in rows)
 if not checks:reasons.append('Independent public cross-check unavailable')
 d={'state':'FAIL' if reasons else 'PASS_UNDERLYING_RESEARCH_ONLY','sample_minutes':n,'quotes_within_5s_pct':ages,'31_bar_tail_qualification_pct':tails,'post_warmup_tail_pct':qualified,'latency_ms':{'min':min(latencies) if n else None,'median':latencies[n//2] if n else None,'p95':p95,'max':max(latencies) if n else None},'public_crosscheck_samples':checks,'reasons':reasons,'live_signal_ready':False,'strategy_validated':False}
 p=(root or ROOT)/'daily_reports'/('LIVE_VERIFY_'+day+'.md');p.parent.mkdir(parents=True,exist_ok=True);temp=p.with_suffix('.pending');temp.write_text('# Live underlying verification — '+day+' ET\n\nMeasured observations only. Public observations have unverified delay; no options or live signal readiness inferred.\n\n```json\n'+json.dumps(d,indent=2)+'\n```\n',encoding='utf-8');os.replace(temp,p);return d
def scheduled(store,now,root=None):
 session=market_session(now);et=now.astimezone(ET);minute=et.hour*60+et.minute
 if not store.get('live_verify_deployment'):store.put('live_verify_deployment',{'at':now.isoformat(),'completed':False})
 state=store.get('live_verify_deployment')
 if (state.get('completed') and state.get('date')==session['date']) or not session['active']:return
 if 575<=minute<635:sample(store,now,root=root)
 if minute>=635 and store.db.execute("SELECT name FROM sqlite_master WHERE name='live_verify_samples'").fetchone():
  count=store.db.execute('SELECT count(*) FROM live_verify_samples WHERE et_date=?',(session['date'],)).fetchone()[0]
  if count:state.update(completed=True,date=session['date']);store.put('live_verify_deployment',state)
if __name__=='__main__':
 s=Store()
 try:print(json.dumps(sample(s)))
 finally:s.close()
