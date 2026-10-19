"""Session/warmup checks using synthetic bars; no price or trade predictions."""
import unittest
from datetime import datetime,timezone,timedelta
from features.indicators import multi_timeframe,normalize,resample,calculate

class MultiFrameBoundaryTests(unittest.TestCase):
    def rows(self,start,count):
        return [{'t':(start+timedelta(minutes=i)).isoformat(),'o':600,'h':602,'l':599,'c':601,'v':100+i} for i in range(count)]
    def test_premarket_and_after_hours_do_not_enter_regular_features(self):
        start=datetime(2026,10,6,12,tzinfo=timezone.utc)
        rows=self.rows(start,600);now=start+timedelta(hours=12)
        result=normalize(rows,now=now)
        self.assertEqual(len(result),390)
        self.assertEqual(result[0]['timestamp'],datetime(2026,10,6,13,30,tzinfo=timezone.utc).timestamp())
        self.assertEqual(result[-1]['timestamp'],datetime(2026,10,6,19,59,tzinfo=timezone.utc).timestamp())
        self.assertEqual(len(resample(result,5)),78)
    def test_early_close_drops_partial_hour_and_late_bars(self):
        start=datetime(2026,11,27,14,30,tzinfo=timezone.utc)
        rows=self.rows(start,390);now=datetime(2026,11,27,22,tzinfo=timezone.utc)
        result=multi_timeframe(rows,now=now)
        self.assertEqual(result['1m']['bars'],210)
        self.assertEqual(result['5m']['bars'],42)
        self.assertEqual(result['30m']['bars'],7)
        self.assertEqual(result['1h']['bars'],3)
    def test_gap_invalidates_opening_range_and_affected_aggregates(self):
        start=datetime(2026,10,6,13,30,tzinfo=timezone.utc)
        rows=self.rows(start,30);rows.pop(6)
        result=multi_timeframe(rows,now=start+timedelta(minutes=30))
        self.assertIsNone(result['opening_range'])
        self.assertEqual(result['5m']['bars'],5)
        self.assertEqual(result['15m']['bars'],1)
        self.assertEqual(result['30m']['status'],'UNAVAILABLE')
    def test_completed_bar_boundary_and_volume_conservation(self):
        start=datetime(2026,10,6,13,30,tzinfo=timezone.utc);rows=self.rows(start,10)
        result=normalize(rows,now=start+timedelta(minutes=10)-timedelta(microseconds=1))
        self.assertEqual(len(result),9);self.assertEqual(len(resample(result,5)),1)
        result=normalize(rows,now=start+timedelta(minutes=10));five=resample(result,5)
        self.assertEqual(len(five),2);self.assertEqual(sum(x['volume'] for x in five),sum(x['volume'] for x in result))
    def test_warmup_is_independent_for_each_timeframe(self):
        start=datetime(2026,10,6,13,30,tzinfo=timezone.utc)
        result=multi_timeframe(self.rows(start,200),now=start+timedelta(minutes=200))
        self.assertIsNotNone(result['1m']['ema200'])
        self.assertIsNone(result['5m']['ema50']);self.assertIsNone(result['5m']['ema200'])
        self.assertIsNone(result['1h']['rsi14']);self.assertEqual(result['daily']['status'],'UNAVAILABLE')
    def test_holiday_bars_are_not_regular_session_data(self):
        start=datetime(2026,12,25,14,30,tzinfo=timezone.utc)
        result=multi_timeframe(self.rows(start,390),now=start+timedelta(hours=8))
        self.assertEqual(result['1m']['status'],'UNAVAILABLE');self.assertIsNone(result['opening_range'])

if __name__=='__main__':unittest.main()
