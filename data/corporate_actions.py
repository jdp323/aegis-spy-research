"""Bounded market-data-only SPY dividend history; no broker/account endpoints."""
from datetime import date,datetime,timezone,timedelta
from data.models import finite
from decimal import Decimal,InvalidOperation

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
            try:rate=Decimal(str(e.get('rate')))
            except InvalidOperation:raise ValueError('CORPORATE_DIVIDEND_INVALID')
            if e.get('symbol')!='SPY' or not rate.is_finite() or rate<0 or isinstance(e.get('rate'),bool):raise ValueError('CORPORATE_DIVIDEND_INVALID')
            ex=date.fromisoformat(e['ex_date']);rows.append({'ex_date':ex.isoformat(),'rate':float(rate)})
        page=raw.get('next_page_token')
        if not page:break
        if page in seen:raise ValueError('CORPORATE_PAGINATION_INVALID')
        seen.add(page)
    else:raise ValueError('CORPORATE_PAGINATION_INCOMPLETE')
    # Official endpoint start/end filter PROCESS_DATE, not EX_DATE. Absence in
    # this response cannot verify zero dividend on every requested ex-date.
    by={}
    for r in rows:
        if start<=r['ex_date']<=end:by[r['ex_date']]=by.get(r['ex_date'],0.)+r['rate']
    return {'status':'OBSERVED_PROCESS_DATE_ACTIONS_ONLY','ex_date_coverage_verified':False,'fetched_at':datetime.now(timezone.utc).isoformat(),
        'source':'https://data.alpaca.markets/v1/corporate-actions','start':start,'end':end,'dividends':by,
        'limitation':'Query filters process_date; unreturned ex-dates remain unknown, never zero. Provider may revise delayed actions; not contemporaneous evidence.'}
