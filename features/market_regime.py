"""Conservative descriptive regime; never a probability forecast."""
def classify(f,quality='DATA_OK',vix=None):
    if quality!='DATA_OK':return {'regime':'UNSAFE','reason':'Data quality is not DATA_OK'}
    needed=['ema9','ema21','ema50','atr14','rsi14','vwap_approx','realized_volatility_per_bar']
    if any(f.get(k) is None for k in needed):return {'regime':'UNSAFE','reason':'Insufficient indicator history'}
    price=f['close'];atr=f['atr14']
    if atr<=0:return {'regime':'ABNORMAL','reason':'Zero true range'}
    if abs(f.get('gap') or 0)>5*atr:return {'regime':'ABNORMAL','reason':'Gap exceeds five observed ATRs'}
    if (vix is not None and vix>=30) or atr/price>.01 or f['realized_volatility_per_bar']>.005:regime='HIGH_VOLATILITY'
    elif abs(f['ema9']-f['ema21'])<atr*.15 and 40<=f['rsi14']<=60:regime='CHOPPY'
    elif price>f['vwap_approx'] and f['ema9']>f['ema21']>f['ema50']:regime='STRONG_BULL' if f['structure']=='HH_HL' and (f.get('rvol_same_slot') or 0)>=1.2 else 'BULL'
    elif price<f['vwap_approx'] and f['ema9']<f['ema21']<f['ema50']:regime='STRONG_BEAR' if f['structure']=='LH_LL' and (f.get('rvol_same_slot') or 0)>=1.2 else 'BEAR'
    else:regime='NEUTRAL'
    return {'regime':regime,'reason':'Descriptive EMA/VWAP/structure/volatility rule v1','vix':vix,'predictive':False}
