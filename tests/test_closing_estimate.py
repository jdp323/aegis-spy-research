import json,math,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from core.sessions import ET,market_session
from tests.test_research_alerts import NOW,fixture
from monitoring.research_alerts import observe,text_for
from research.closing_estimate import estimate,quantile,URL,load,refresh

def history(count=50):
    rows=[];day=datetime(2026,6,1,9,30,tzinfo=ET);i=0
    while i<count:
        s=market_session(day)
        if s['active']:
            base=500+i;end=s['close_minute'];factor=(i%7-3)*.001
            for minute in range(570,end,5):
                t=day.replace(hour=minute//60,minute=minute%60)
                px=base*(1+factor*(minute-570)/(end-575))
                rows.append({'timestamp':int(t.timestamp()),'open':px,'high':px+1,'low':px-1,'close':px,'volume':100})
            i+=1
        day+=timedelta(days=1)
    return {'source':URL,'symbol':'SPY','quality':'PUBLIC_HISTORY','fetched_at':NOW.isoformat(),'sha256':'a'*64,'bars':rows}

class ClosingEstimateTests(unittest.TestCase):
 def observation(self,now=NOW):return observe(fixture(now),market_session(now),now)
 def test_history_scenarios_are_not_live_trade_signal(self):
    f=estimate(self.observation(),market_session(NOW),history(),NOW)
    self.assertEqual(f['status'],'EXPERIMENTAL_SCENARIOS');self.assertFalse(f['validated']);self.assertEqual(f['action'],'NO TRADE')
    self.assertLessEqual(f['low'],f['median']);self.assertLessEqual(f['median'],f['high']);self.assertGreaterEqual(f['chronological_test_sessions'],10)
    self.assertGreaterEqual(f['historical_mae_usd'],0);self.assertIn('not official',f['limitations']);self.assertIn('not a calibrated',f['limitations'].lower())
 def test_minimum_history_missing_bar_and_stale_inputs(self):
    h=history(39);self.assertEqual(estimate(self.observation(),market_session(NOW),h,NOW)['status'],'UNAVAILABLE')
    h=history(40);h['bars'].pop(30);self.assertEqual(estimate(self.observation(),market_session(NOW),h,NOW)['status'],'UNAVAILABLE')
    h=history();h['fetched_at']=(NOW-timedelta(days=2)).isoformat();self.assertEqual(estimate(self.observation(),market_session(NOW),h,NOW)['reason'],'HISTORY_STALE')
 def test_duplicate_or_invalid_bars_rejected(self):
    for bad in ('duplicate','invalid'):
        h=history()
        if bad=='duplicate':h['bars'].append(h['bars'][0].copy())
        else:h['bars'][0]['close']=float('nan')
        self.assertEqual(estimate(self.observation(),market_session(NOW),h,NOW)['reason'],'HISTORY_SCHEMA_INVALID')
 def test_current_and_future_session_outcomes_never_used(self):
    h=history();first=estimate(self.observation(),market_session(NOW),h,NOW)
    today=history(1)['bars'];offset=int(NOW.replace(hour=13,minute=30).timestamp())-today[0]['timestamp']
    h['bars']+=[{**r,'timestamp':r['timestamp']+offset,'close':r['close']*100} for r in today]
    second=estimate(self.observation(),market_session(NOW),h,NOW)
    self.assertEqual(first,second)
 def test_inactive_stale_observation_and_near_close(self):
    closed=NOW.replace(hour=21);self.assertEqual(estimate(self.observation(),market_session(closed),history(),closed)['status'],'UNAVAILABLE')
    near=NOW.replace(hour=19,minute=55);self.assertEqual(estimate(self.observation(near),market_session(near),history(),near)['reason'],'SESSION_CLOSE_TOO_NEAR')
    self.assertEqual(estimate({'quality':'UNAVAILABLE'},market_session(NOW),history(),NOW)['status'],'UNAVAILABLE')
 def test_compact_message_separates_observation_forecast_and_decision(self):
    f=estimate(self.observation(),market_session(NOW),history(),NOW)
    with patch('research.closing_estimate.estimate',return_value=f):text=text_for(self.observation(),market_session(NOW),NOW)
    for field in ('ACTION: NO TRADE','TREND: BULLISH','CLOSING AREA — EXPERIMENTAL','CALL / PUT: No recommendation','ENTRY / STOP / TARGET: Not issued','Delay UNVERIFIED'):self.assertIn(field,text)
    self.assertLess(len(text),1200)
    for jargon in ('HIGHER_HIGHS_HIGHER_LOWS','BAR_HISTORY_STALE_OR_UNAVAILABLE','{'):self.assertNotIn(jargon,text)
 def test_failed_history_attempt_is_not_repeated_same_day(self):
    with tempfile.TemporaryDirectory() as d,patch('research.closing_estimate.ROOT',Path(d)),patch('research.closing_estimate.urllib.request.urlopen',side_effect=TimeoutError) as call:
        (Path(d)/'research').mkdir();a=refresh(NOW);b=refresh(NOW+timedelta(hours=1));self.assertEqual(call.call_count,1);self.assertEqual(a,b);self.assertEqual(a['quality'],'UNAVAILABLE')
 def test_cache_tampering_fails_closed(self):
    with tempfile.TemporaryDirectory() as d,patch('research.closing_estimate.ROOT',Path(d)):
        root=Path(d);(root/'research').mkdir();(root/'data/closing_cache').mkdir(parents=True)
        h=history();(root/'research/closing_history.json').write_text(json.dumps(h));(root/'data/closing_cache'/('a'*64+'.json')).write_text('changed')
        self.assertIsNone(load(NOW))
 def test_quantiles(self):
    self.assertEqual(quantile([1,2,3,4,5],.5),3);self.assertEqual(quantile([1,2,3,4,5],0),1);self.assertEqual(quantile([1,2,3,4,5],1),5)

if __name__=='__main__':unittest.main()
