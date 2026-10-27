import json,threading,time,unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from monitoring.receipt_observer import ReceiptObserver
from ops.session_report import receipts

class ReceiptObservation(unittest.TestCase):
    def test_blocked_scan_never_blocks_market_poll_and_is_single_flight(self):
        entered=threading.Event();release=threading.Event();calls=[];clock=[0.]
        def scan(root,day):calls.append(day);entered.set();release.wait(2);return [{'status':'UNCERTAIN_AFTER_SEND'}]
        observer=ReceiptObserver(Path('.'),scan=scan,clock=lambda:clock[0],budget=.1)
        try:
            start=time.monotonic();rows,health=observer.poll('2026-10-27');self.assertLess(time.monotonic()-start,.2);self.assertIsNone(rows);self.assertTrue(entered.wait(1))
            clock[0]=1.;rows,health=observer.poll('2026-10-27');self.assertEqual(health['state'],'OVER_BUDGET');self.assertIsNone(rows);self.assertEqual(len(calls),1)
            release.set();observer.thread.join(1);rows,health=observer.poll('2026-10-27');self.assertEqual(rows,[{'status':'UNCERTAIN_AFTER_SEND'}]);self.assertEqual(health['state'],'CURRENT')
        finally:release.set();observer.close()
    def test_failure_is_unknown_not_zero_uncertain_deliveries(self):
        observer=ReceiptObserver(Path('.'),scan=lambda *a:(_ for _ in ()).throw(TimeoutError('fixture')))
        try:
            observer.poll('2026-10-27');observer.thread.join(1);rows,health=observer.poll('2026-10-27');self.assertIsNone(rows);self.assertEqual(health['state'],'FAILED');self.assertEqual(health['error_type'],'TimeoutError')
        finally:observer.close()
    def test_old_day_values_are_not_reused_as_today(self):
        observer=ReceiptObserver(Path('.'),scan=lambda *a:[{'status':'TELEGRAM_ACCEPTED'}])
        try:
            observer.poll('2026-10-26');observer.thread.join(1);rows,_=observer.poll('2026-10-27');self.assertIsNone(rows)
        finally:observer.close()
    def test_close_is_bounded_and_does_not_launch_new_scan(self):
        release=threading.Event();observer=ReceiptObserver(Path('.'),scan=lambda *a:release.wait(2) or [])
        observer.poll('2026-10-27');start=time.monotonic();observer.close();self.assertLess(time.monotonic()-start,.5);release.set();observer.thread.join(1);old=observer.thread;observer.poll('2026-10-28');self.assertIs(observer.thread,old)
    def test_budgeted_real_parser_fails_without_partial_zero_summary(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);folder=root/'logs/notifications';folder.mkdir(parents=True);(folder/'one.json').write_text(json.dumps({'created_at':'2026-10-27T12:00:00Z','status':'UNCERTAIN_AFTER_SEND'}))
            with patch('ops.session_report.time.monotonic',side_effect=[0.,2.]):
                with self.assertRaises(TimeoutError):receipts(root,'2026-10-27',budget_seconds=1)
            (folder/'one.json').write_text('x'*65537)
            with self.assertRaisesRegex(ValueError,'TOO_LARGE'):receipts(root,'2026-10-27',budget_seconds=1)
if __name__=='__main__':unittest.main()
