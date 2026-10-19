"""Malformed provider timestamps must become DATA_INVALID, not worker crashes."""
import unittest
from datetime import datetime,timezone
from data.models import Datum,Quality,stamp,quote

NOW=datetime(2026,10,5,17,34,tzinfo=timezone.utc)

class TimestampSchemaTests(unittest.TestCase):
 def test_non_string_timestamps_reject_with_value_error(self):
    for value in (123,True,[],{},float('nan'),None,'','x'*65):
        with self.subTest(value=value),self.assertRaises(ValueError):stamp(value)
 def test_bad_source_schema_fails_closed_in_view(self):
    for value in (123,True,['2026-10-05'],{'t':'2026-10-05'},'not-a-timestamp','2026-10-05T17:34:00'):
        with self.subTest(value=value):
            d=quote('fixture','SPY',{'bp':600,'ap':601,'t':value},received=NOW.isoformat()).view(NOW)
            self.assertEqual(d['quality'],Quality.INVALID)
 def test_bad_received_schema_fails_closed_in_view(self):
    for value in (123,{},[],True,'not-a-timestamp'):
        d=Datum('fixture','SPY','quote',NOW.isoformat(),value,Quality.OK,'REALTIME').view(NOW)
        self.assertEqual(d['quality'],Quality.INVALID)
 def test_missing_source_cannot_be_valid_and_valid_offset_preserved(self):
    self.assertEqual(Datum('fixture','SPY','quote',quality=Quality.OK).view(NOW)['quality'],Quality.INCOMPLETE)
    self.assertEqual(stamp('2026-10-05T13:34:00-04:00'),NOW)
    self.assertEqual(stamp('2026-10-05T17:34:00Z'),NOW)

if __name__=='__main__':unittest.main()
