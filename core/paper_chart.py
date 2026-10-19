"""Standalone SPY five-minute PNG from completed feed bars; no invented chart data."""
from pathlib import Path
import sys
from datetime import datetime,timezone
from core.storage import ROOT
from core.sessions import ET
from features.indicators import normalize,resample
def generate(store,signal,now):
 vendor=str(Path(__file__).resolve().parents[1]/'.vendor')
 if vendor not in sys.path:sys.path.insert(0,vendor)
 import matplotlib
 matplotlib.use('Agg')
 from matplotlib import pyplot as plt
 feed=signal.get('feed_quality');rows=store.get('stream_bars:SPY' if feed=='SIP' else 'research_stream_bars:SPY:iex',[]);bars=resample(normalize(rows,now=now),5);bars=[b for b in bars if datetime.fromtimestamp(b['timestamp'],timezone.utc).astimezone(ET).date()==now.astimezone(ET).date()]
 if len(bars)<6:raise ValueError('CHART_HISTORY_INCOMPLETE')
 x=[datetime.fromtimestamp(b['timestamp'],timezone.utc).astimezone(ET) for b in bars];close=[b['close'] for b in bars];volume=total=0;vw=[]
 for b in bars:
  volume+=b['volume'];total+=(b['high']+b['low']+b['close'])/3*b['volume'];vw.append(total/volume if volume else float('nan'))
 fig,ax=plt.subplots(figsize=(10,5));ax.plot(x,close,label='SPY completed 5m close');ax.plot(x,vw,label='Bar VWAP approximation')
 for key,color in [('spy_price','blue'),('invalidation','red'),('t1','green'),('t2','darkgreen')]:
  if signal.get(key) is not None:ax.axhline(signal[key],label=key,color=color,linestyle='--',alpha=.6)
 ax.set_title('AEGIS PAPER / UNVALIDATED — '+str(feed)+' | '+now.astimezone(ET).strftime('%Y-%m-%d %H:%M ET'));ax.set_ylabel('USD/share');ax.legend(loc='best');fig.autofmt_xdate();fig.tight_layout();folder=ROOT/'daily_reports/charts';folder.mkdir(parents=True,exist_ok=True);p=folder/(signal['signal_id']+'.png');fig.savefig(p,dpi=140);plt.close(fig);return p
