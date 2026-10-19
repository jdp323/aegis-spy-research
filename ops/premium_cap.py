"""Measured premium-cap rejections; unverified quotes are excluded from premium statistics."""
import hashlib,statistics,json
from core.signals import option_quote_valid
def observe(store,selection,config,now):
    for c in selection.get('rejected',[]):
        if not set(c.get('reasons',[])) & {'PREMIUM_LIMIT','PREMIUM_ABOVE_CAP'}:continue
        if not option_quote_valid(c.get('quote',{}),now):continue
        id=hashlib.sha256((c['symbol']+c['quote']['source_timestamp']).encode()).hexdigest()[:24]
        store.event('premium-cap-'+id,'premium_cap_rejection',{'symbol':c['symbol'],'timestamp':now.isoformat(),'premium_usd':c['ask']*100,'cap_usd':config['options_risk']['max_trade_premium_usd'],'feed_quality':c['quote'].get('feed_quality','OPRA')})
def report(store):
    rows=store.events('premium_cap_rejection',100000);values=[r['premium_usd'] for r in rows]
    return {'verified_quote_rejection_samples':len(rows),'mean_rejected_premium_usd':statistics.mean(values) if values else None,'median_rejected_premium_usd':statistics.median(values) if values else None,'basis':'Distinct contract/source-quote timestamps; only fresh verified real quotes at observation. Not a trade opportunity count.','cap_usd':500,'state':'MEASURED' if rows else 'INSUFFICIENT_DATA'}
