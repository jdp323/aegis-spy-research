"""Misaligned OHLCV must not create opening ranges or multi-frame evidence."""
import unittest
from datetime import datetime,timezone,timedelta
from features.indicators import normalize,multi_timeframe

class MinuteAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.start=datetime(2026,10,6,13,30,tzinfo=timezone.utc)
        self.now=self.start+timedelta(minutes=30)
    def row(self,time):
        return {'t':time.isoformat(),'o':600,'h':602,'l':599,'c':601,'v':100}
    def test_seconds_and_subseconds_are_rejected_for_intraday_features(self):
        for offset in (timedelta(seconds=1),timedelta(seconds=30),timedelta(microseconds=1),timedelta(seconds=59,microseconds=999999)):
            for minutes in (1,5,15):
                with self.subTest(offset=offset,minutes=minutes):
                    with self.assertRaisesRegex(ValueError,'MISALIGNED_BAR_TIMESTAMP'):
                        normalize([self.row(self.start+offset)],minutes=minutes,now=self.now)
    def test_fractional_epoch_timestamp_is_rejected(self):
        row=self.row(self.start);row.pop('t');row['timestamp']=self.start.timestamp()+0.5
        with self.assertRaisesRegex(ValueError,'MISALIGNED_BAR_TIMESTAMP'):
            normalize([row],now=self.now)
        for value in ('2026-10-06T13:30:00.000000001Z','2026-10-06T13:30:00+00:00:30'):
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,'MISALIGNED_BAR_TIMESTAMP'):
                normalize([{**self.row(self.start),'t':value}],now=self.now)
    def test_shifted_minute_series_cannot_establish_opening_range(self):
        rows=[self.row(self.start+timedelta(minutes=i,seconds=30)) for i in range(15)]
        with self.assertRaisesRegex(ValueError,'MISALIGNED_BAR_TIMESTAMP'):
            multi_timeframe(rows,now=self.now)
    def test_timezone_equivalent_aligned_minute_is_preserved(self):
        utc=self.row(self.start);offset={**utc,'t':'2026-10-06T09:30:00-04:00'}
        self.assertEqual(normalize([utc],now=self.now),normalize([offset],now=self.now))
        self.assertEqual(len(normalize([utc],now=self.start+timedelta(minutes=1))),1)

if __name__=='__main__':unittest.main()
