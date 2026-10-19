from dataclasses import dataclass,field,asdict
from enum import StrEnum
from datetime import datetime,timezone
import math
class Quality(StrEnum):
    OK='DATA_OK';STALE='DATA_STALE';INCOMPLETE='DATA_INCOMPLETE';INVALID='DATA_INVALID';DISCONNECTED='FEED_DISCONNECTED';UNCONFIGURED='FEED_NOT_CONFIGURED'
def stamp(value):
    if not isinstance(value,str) or not value or len(value)>64:
        raise ValueError('timestamp requires an ISO string with offset')
    t=datetime.fromisoformat(value.replace('Z','+00:00'))
    if t.tzinfo is None:raise ValueError('timestamp requires offset')
    return t
def finite(v):return type(v) in (int,float) and math.isfinite(v)
@dataclass
class Datum:
    provider:str
    symbol:str
    data_type:str
    source_timestamp:str|None=None
    received_timestamp:str=field(default_factory=lambda:datetime.now(timezone.utc).isoformat())
    quality:str=Quality.INCOMPLETE
    entitlement:str='UNAVAILABLE'
    payload:dict=field(default_factory=dict)
    sequence:int|None=None
    reason:str=''
    def view(self,now=None,max_age=15,max_future_skew_seconds=0):
        now=now or datetime.now(timezone.utc);d=asdict(self);d['timestamp']=self.source_timestamp;d['freshness_seconds']=None;d['latency_ms']=None
        if self.source_timestamp:
            try:
                age=(now-stamp(self.source_timestamp)).total_seconds();latency=(stamp(self.received_timestamp)-stamp(self.source_timestamp)).total_seconds()*1000
                d.update(freshness_seconds=age,latency_ms=latency)
                if age < -max_future_skew_seconds or latency < -1000*max_future_skew_seconds:d['quality']=Quality.INVALID
                elif age<0 or latency<0:d['accepted_future_skew_seconds']=max_future_skew_seconds
                elif age>max_age and self.quality==Quality.OK:d['quality']=Quality.STALE
            except (ValueError,TypeError):d['quality']=Quality.INVALID
        elif self.quality==Quality.OK:d['quality']=Quality.INCOMPLETE
        return d
def quote(provider,symbol,q,entitlement='REALTIME',received=None):
    received=received or datetime.now(timezone.utc).isoformat();bid=q.get('bp');ask=q.get('ap')
    good=finite(bid) and finite(ask) and 0<bid<=ask
    return Datum(provider,symbol,'quote',q.get('t'),received,Quality.OK if good else Quality.INVALID,entitlement,{'bid':bid,'ask':ask,'mid':(bid+ask)/2 if good else None},q.get('sequence'))
def unavailable(provider,symbol,kind,quality=Quality.UNCONFIGURED,reason='UNAVAILABLE'):return Datum(provider,symbol,kind,quality=quality,reason=reason)
