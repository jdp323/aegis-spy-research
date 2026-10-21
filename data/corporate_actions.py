"""Bounded market-data-only SPY dividend history; no broker/account endpoints."""
from datetime import date,datetime,timezone,timedelta
from data.models import finite

def collect(provider,start,end):
    a=date.fromisoformat(start);b=date.fromisoformat(end)
    if not 0<=(b-a).days<=90:raise ValueError('CORPORATE_RANGE_INVALID')
    page=None;seen=set();rows=[]
    for _ in range(5):
        params={'symbols':'SPY','types':'cash_dividend','start':start,'end':end,'limit':1000,'data_quality':'complete'}
        if page:params['page_token']=page
        raw=provider.get('/v1/corporate-actions',params)
        events=(raw.get('corporate_actions') or {}).get('cash_dividends')
        if not isinstance(events,list):raise ValueError('CORPORATE_SCHEMA_UNAVAILABLE')
        for e in events:
            if e.get('symbol')!='SPY' or not finite(e.get('rate')) or e['rate']<0:raise ValueError('CORPORATE_DIVIDEND_INVALID')
            ex=date.fromisoformat(e['ex_date']);rows.append({'ex_date':ex.isoformat(),'rate':e['rate']})
        page=raw.get('next_page_token')
        if not page:break
        if page in seen:raise ValueError('CORPORATE_PAGINATION_INVALID')
        seen.add(page)
    else:raise ValueError('CORPORATE_PAGINATION_INCOMPLETE')
    by={};cursor=a
    while cursor<=b:by[cursor.isoformat()]=0.;cursor+=timedelta(days=1)
    for r in rows:
        if r['ex_date'] in by:by[r['ex_date']]+=r['rate']
    return {'status':'COMPLETE_PROVIDER_RESPONSE','fetched_at':datetime.now(timezone.utc).isoformat(),
        'source':'https://data.alpaca.markets/v1/corporate-actions','start':start,'end':end,'dividends':by,
        'limitation':'Provider may revise delayed corporate actions; downloaded history is not contemporaneous evidence.'}
