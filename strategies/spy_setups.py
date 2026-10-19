"""Descriptive completed-bar setups with explicit confirmation blockers."""
VERSION='spy-opening-vwap-v3'
def detect(features,price):
 f=features.get('5m',{});opening=features.get('opening_range');close=f.get('close');vwap=f.get('vwap_approx');previous=f.get('previous_close');prior_vwap=f.get('previous_vwap_approx');sign=0;setup='UNAVAILABLE';stop=None;reasons=[]
 if price is not None and opening:
  if price>opening['high']:sign=1;setup='OPENING_RANGE_BREAKOUT';stop=opening['high']
  elif price<opening['low']:sign=-1;setup='OPENING_RANGE_BREAKOUT';stop=opening['low']
 if not sign and all(v is not None for v in (price,close,vwap,previous,prior_vwap)):
  if previous<=prior_vwap and close>vwap and price>vwap:sign=1;setup='VWAP_RECLAIM';stop=min(vwap,f.get('previous_low',vwap))
  elif previous>=prior_vwap and close<vwap and price<vwap:sign=-1;setup='VWAP_REJECTION';stop=max(vwap,f.get('previous_high',vwap))
 if not sign:return {'setup_type':'UNAVAILABLE','sign':0,'invalidation':None,'reasons':['NO_CONFIRMED_SETUP']}
 if close is None or (close-stop)*sign<=0:reasons.append('COMPLETED_BAR_SETUP_NOT_CONFIRMED')
 if f.get('rvol_same_slot') is None or f['rvol_same_slot']<1.2:reasons.append('VOLUME_CONFIRMATION_MISSING')
 if setup!='OPENING_RANGE_BREAKOUT':
  if f.get('structure')!=('HH_HL' if sign==1 else 'LH_LL'):reasons.append('STRUCTURE_CONFIRMATION_MISSING')
  if any(features.get(k,{}).get('trend')==('BEAR' if sign==1 else 'BULL') for k in ('15m','30m','1h','daily')):reasons.append('HIGHER_TIMEFRAME_CONTRADICTS')
 return {'setup_type':setup,'sign':sign,'invalidation':stop,'reasons':reasons,'strategy_version':VERSION}
