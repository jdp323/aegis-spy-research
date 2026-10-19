import unittest,tempfile,json,hashlib
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from research.basic_trend import analyze,text_for
from data.premarket_spy import URL
from core.sessions import market_session
from monitoring.research_alerts import short_text
NOW=datetime(2026,10,6,12,55,tzinfo=timezone.utc)
class BasicTrendTests(unittest.TestCase):
    def raw(self,direction=1,volume=0):
        bars=[]
        for i in range(15):
            p=600+direction*i;bars.append({'timestamp':int((NOW-timedelta(minutes=(15-i)*5)).timestamp()),'open':p,'high':p+1,'low':p-1,'close':p,'volume':volume})
        return {'source':URL,'symbol':'SPY','status':'RESEARCH_DATA_RECEIVED','use':'DELAY_UNVERIFIED_RESEARCH_ONLY','fetched_at':NOW.isoformat(),'bars':bars,'sha256':'fixture'}
    def read(self,raw,now=NOW):
        with patch('research.basic_trend.verified',return_value=True):return analyze(raw,now)
    def test_up_down_and_flat_are_descriptive(self):
        for direction,label in ((1,'UP'),(-1,'DOWN'),(0,'MIXED')):
            r=self.read(self.raw(direction));self.assertEqual(r['direction'],label);self.assertEqual(r['scope'],'PREMARKET');self.assertIn('08:55 ET',text_for(r));self.assertIn('delay unverified',text_for(r));self.assertNotIn('BUY',text_for(r))
    def test_zero_volume_allows_price_only_never_vwap_confirmation(self):
        r=self.read(self.raw());self.assertEqual(r['direction'],'UP');self.assertIsNone(r['vwap_approx']);self.assertEqual(r['volume_confirmation'],'UNAVAILABLE')
    def test_source_hash_must_match_actual_parsed_rows(self):
        from data.public_spy import parse_chart
        raw=self.raw();rows=raw['bars'];body=json.dumps({'chart':{'result':[{'meta':{'symbol':'SPY'},'timestamp':[b['timestamp'] for b in rows],'indicators':{'quote':[{k:[b[k] for b in rows] for k in ('open','high','low','close','volume')}]}}]}}).encode();digest=hashlib.sha256(body).hexdigest()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'data/premarket_cache').mkdir(parents=True);(root/'data/premarket_cache'/(digest+'.json')).write_bytes(body);raw['sha256']=digest
            with patch('data.premarket_spy.ROOT',root):
                self.assertEqual(analyze(raw,NOW)['direction'],'UP');raw['bars'][-1]['close']+=.1;self.assertEqual(analyze(raw,NOW)['direction'],'UNAVAILABLE')
    def test_stale_future_or_incomplete_bars_not_current(self):
        raw=self.raw();raw['fetched_at']=(NOW-timedelta(hours=1)).isoformat();self.assertEqual(self.read(raw)['direction'],'UNAVAILABLE')
        raw=self.raw();raw['fetched_at']=(NOW+timedelta(seconds=1)).isoformat();self.assertEqual(self.read(raw)['direction'],'UNAVAILABLE')
        raw=self.raw();raw['bars'].append({**raw['bars'][-1],'timestamp':int(NOW.timestamp()),'close':float('nan')});self.assertEqual(self.read(raw)['direction'],'UP')
    def test_latest_gap_resets_warmup(self):
        raw=self.raw();del raw['bars'][-3];self.assertEqual(self.read(raw)['direction'],'UNAVAILABLE')
    def test_no_regular_session_yesterday_as_current_premarket(self):
        raw=self.raw()
        for b in raw['bars']:b['timestamp']-=86400
        self.assertEqual(self.read(raw)['direction'],'UNAVAILABLE')
    def test_closed_and_unknown_calendar_never_current(self):
        for now in (NOW.replace(hour=22),NOW.replace(year=2027)):
            raw=self.raw();raw['fetched_at']=now.isoformat();self.assertEqual(self.read(raw,now)['direction'],'UNAVAILABLE')
    def test_source_disagreement_prevents_basic_direction_alert(self):
        with patch('data.trend_spy.load',return_value=self.raw()),patch('research.basic_trend.verified',return_value=True):
            text=short_text({'quality':'UNAVAILABLE','reason':'SOURCE_DISAGREEMENT'},market_session(NOW),NOW)
        self.assertIn('UNAVAILABLE',text);self.assertNotIn('SPY TREND: UP',text)
    def test_tenant_routes_receive_same_public_basic_reading(self):
        from core.bot_commands import execute
        with patch('research.basic_trend.on_demand_text',return_value='SPY TREND: UP'):
            self.assertEqual(execute({'tenant':'owner','command':'trend'}),execute({'tenant':'0'*24,'command':'trend'}))
if __name__=='__main__':unittest.main()
