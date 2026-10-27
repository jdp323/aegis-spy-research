import unittest,copy
from datetime import datetime,timedelta,timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from test_master_boundaries import rows5,result,NOW
from research.shadow_forecast import prepare,validate_result,earlier_session_baseline
from research.shadow_evaluation import evaluate
from ops.master_session import summarize
from core.sessions import ET
from data.corporate_actions import collect

class Evaluation(unittest.TestCase):
    def test_date_only_blackout_remains_visible_after_midnight_and_names_are_one_line(self):
        from monitoring.owner_messages import next_event
        midnight=NOW.astimezone(ET).replace(hour=0,minute=0)
        news={'quality':'DATA_OK','events':[{'name':'FOMC\nfixture','time_utc':midnight.isoformat(),'time_source':'DATE_ONLY','risk':'HIGH'},{'name':'later','time_utc':(NOW+timedelta(days=1)).isoformat()}]}
        self.assertEqual(next_event(news,NOW),'FOMC fixture · all-day ET')
        self.assertIn('unavailable',next_event({'quality':'DATA_OK','events':[{'time_utc':'bad'}]},NOW))
    def test_all_issued_forecasts_and_failures_stay_in_denominator(self):
        q=prepare(rows5(),'IEX',NOW);failed=copy.deepcopy(q);failed['id']='failed';r=validate_result(q,result(q),NOW+timedelta(seconds=1))
        actual=[dict(b,symbol='SPY',feed_quality='IEX') for b in r['paths'][0]['bars']]
        outputs={q['id']:{'validated':r},'failed':{'status':'TIMEOUT'}}
        e=evaluate([q,failed],outputs,actual,NOW+timedelta(hours=2));g=e['groups']['IEX:H60'];self.assertEqual(g['issued'],2);self.assertEqual(g['resolved'],1);self.assertEqual(g['statuses']['TIMEOUT'],1);self.assertFalse(g['qualified']);self.assertIsNone(g['day_block_ci95'])
    def test_future_outcomes_cannot_resolve_before_target(self):
        q=prepare(rows5(),'IEX',NOW);r=validate_result(q,result(q),NOW+timedelta(seconds=1));actual=[dict(b,symbol='SPY',feed_quality='IEX') for b in r['paths'][0]['bars']]
        self.assertEqual(evaluate([q],{q['id']:{'validated':r}},actual,NOW)['rows'][0]['status'],'PENDING')
        self.assertEqual(evaluate([q],{q['id']:{'validated':r}},actual[:-1],NOW+timedelta(hours=2))['rows'][0]['status'],'MISSING_OUTCOME')
    def test_time_of_day_baseline_excludes_future_and_other_feed(self):
        opening=NOW.astimezone(ET).replace(hour=9,minute=30);prior=opening-timedelta(days=1)
        rows=[{'start_at':(prior+timedelta(minutes=5*n)).isoformat(),'open':500.,'close':501.,'feed_quality':'IEX'} for n in range(78)]
        history={prior.date().isoformat():rows,(opening+timedelta(days=1)).date().isoformat():rows}
        r=earlier_session_baseline(history,NOW,500.,60,feed='IEX');self.assertEqual(r['count_sessions'],1)
        self.assertEqual(earlier_session_baseline(history,NOW,500.,60,feed='SIP')['count_sessions'],0)
    def test_all25_slots_denominator_missing_messages_fail_and_risk_wait_separate(self):
        day='2026-10-27';opening=NOW.astimezone(ET).replace(year=2026,month=10,day=27,hour=0,minute=0);receipts={};evidence={};slots=[]
        for minute in range(585,946,15):
            ident='v5-trend-'+day+'-'+str(minute);slots.append(ident);receipts[ident]={'status':'TELEGRAM_ACCEPTED','accepted_at':(opening+timedelta(minutes=minute,seconds=10)).isoformat()};evidence[ident]={'underlying_gates_pass':True,'calendar_refusal':True}
        r=summarize(day,slots,receipts,evidence);self.assertEqual(r['expected_slots'],25);self.assertEqual(r['on_time'],25);self.assertEqual(r['underlying_pass'],25);self.assertTrue(r['schedule_data_target_pass']);self.assertEqual(r['entries']['accepted_count'],0)
        missing=summarize(day,[],{},{});self.assertEqual(missing['expected_slots'],25);self.assertFalse(missing['schedule_data_target_pass']);self.assertEqual(missing['underlying_pass'],0)
    def test_source_date_filter_and_decimal_rates_do_not_invent_zero_days(self):
        class Provider:
            def get(self,*a):return {'corporate_actions':{'cash_dividends':[{'symbol':'SPY','rate':'1.23','ex_date':'2026-10-20'}]}}
        r=collect(Provider(),'2026-10-19','2026-10-21');self.assertEqual(r['dividends'],{'2026-10-20':1.23});self.assertFalse(r['ex_date_coverage_verified']);self.assertIn('process_date',r['limitation'])
if __name__=='__main__':unittest.main()
