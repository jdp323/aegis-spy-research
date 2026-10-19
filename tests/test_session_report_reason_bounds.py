"""Bounded truthful reason summaries preserve all raw historical trace payloads."""
import hashlib,json,sqlite3,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from core.sessions import ET
from core.rejection_trace import reason_codes,measure,summary
from ops.day_simulation import config
from ops.session_report import collect,write

class ReasonBounds(unittest.TestCase):
    def test_explicit_predicate_is_additive_and_legacy_inference_is_labelled(self):
        now=datetime(2026,10,16,10,tzinfo=ET)
        raw='Quote rejected: source age exceeds 5 s; source age +7.245 s'
        traces=measure({'reason':raw,'failed_predicate':'SOURCE_TOO_OLD'}, {},config(),now)
        self.assertTrue(traces)
        for trace in traces:
            self.assertEqual(trace['blocker'],raw);self.assertEqual(trace['blocker_code'],'SOURCE_TOO_OLD')
            self.assertEqual(reason_codes(trace),['SOURCE_TOO_OLD'])
        self.assertEqual(reason_codes({'blocker':raw}),['LEGACY_INFERRED_SOURCE_TOO_OLD'])
        self.assertEqual(reason_codes({'blocker':'data not fresh — '+raw}),['LEGACY_INFERRED_SOURCE_TOO_OLD'])
        self.assertEqual(reason_codes({'blocker':'feed heartbeat not fresh: signed heartbeat age +41.532 s; budget 30 s'}),['LEGACY_INFERRED_HEARTBEAT_AGE'])
        self.assertEqual(reason_codes({'blocker':'data not fresh (last quote 0 s old)'}),['LEGACY_UNKNOWN_BLOCKER'])
        self.assertEqual(reason_codes({'blocker':'NEWS_BLACKOUT'}),['LEGACY_STORED_NEWS_BLACKOUT'])
        self.assertEqual(reason_codes({'blocker':raw,'blocker_code':'NEW_UNRECOGNIZED_999'}),['EXPLICIT_OTHER_PREDICATE'])
        self.assertEqual(reason_codes({'checks':{'volume_ratio':{'state':'FAIL'},'some_new_check':{'state':'FAIL'}}}),['CHECK_VOLUME_RATIO','UNKNOWN_FAILED_CHECK'])

    def test_thousands_of_varying_ages_produce_small_report_and_preserve_payloads(self):
        day='2026-10-16';opening=datetime(2026,10,16,9,30,tzinfo=ET);end=opening+timedelta(minutes=390)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'runtime').mkdir();(root/'config').mkdir();(root/'monitoring/outbox').mkdir(parents=True)
            (root/'config/upgrade.json').write_text(json.dumps({'live_signal_enabled':False,'order_execution_enabled':False,'max_future_skew_seconds':2}))
            path=root/'runtime/observability.sqlite';db=sqlite3.connect(path)
            db.execute('CREATE TABLE rejection_traces(minute TEXT,setup TEXT,direction TEXT,version TEXT,snapshot_id TEXT,payload TEXT,evaluation_count INTEGER,PRIMARY KEY(minute,setup,direction,version))')
            values=[]
            for minute in range(510):
                at=(opening+timedelta(minutes=minute)).astimezone(timezone.utc).isoformat()
                for setup in range(10 if minute<390 else 1):
                    raw=f'Quote rejected: source age exceeds 5 s; source age +{minute}.{setup:03d} s, receipt age +{setup}.{minute:03d} s, skew -{minute}.{setup:03d} s; provider alpaca-iex; exact source/receipt/evaluation diagnostics retained in raw record; no fabricated quote.'
                    payload=json.dumps({'at':at,'blocker':raw,'checks':{},'frames':{k:'UNAVAILABLE' for k in ('1m','5m','15m','30m','1h','daily')}})
                    values.append((at,'fixture_'+str(setup),'CALL','fixture',hashlib.sha256(payload.encode()).hexdigest()[:24],payload,1))
            for setup in range(10):
                at=(opening-timedelta(minutes=1)).astimezone(timezone.utc).isoformat();payload=json.dumps({'at':at,'blocker':'premarket fixture; not a regular-session setup','checks':{},'frames':{}})
                values.append((at,'premarket_'+str(setup),'CALL','fixture',hashlib.sha256(payload.encode()).hexdigest()[:24],payload,1))
            db.executemany('INSERT INTO rejection_traces VALUES(?,?,?,?,?,?,?)',values);db.commit()
            before=db.execute('SELECT minute,setup,payload,evaluation_count FROM rejection_traces ORDER BY minute,setup').fetchall();db.close()
            result=collect(day,root,end+timedelta(minutes=20))
            self.assertEqual(result['idea_engine']['trace_count'],3900)
            self.assertEqual(result['idea_engine']['outside_regular_session_trace_rows'],130)
            by_hour=result['idea_engine']['rejection_reasons_by_hour']
            self.assertEqual(sum(sum(values.values()) for values in by_hour.values()),3900)
            self.assertEqual(set().union(*(set(v) for v in by_hour.values())),{'LEGACY_INFERRED_SOURCE_TOO_OLD'})
            self.assertNotIn('16:00 ET',by_hour);self.assertEqual(len(by_hour),7)
            report=write(day,root,end+timedelta(minutes=20))
            self.assertLess(report.stat().st_size,60000);self.assertLess(report.with_suffix('.json').stat().st_size,60000)
            self.assertNotIn('exact source/receipt/evaluation diagnostics',report.read_text(encoding='utf-8'))
            text=summary(path,end+timedelta(minutes=15));self.assertIn('LEGACY_INFERRED_SOURCE_TOO_OLD 3900',text);self.assertLess(len(text),1000)
            db=sqlite3.connect(path);after=db.execute('SELECT minute,setup,payload,evaluation_count FROM rejection_traces ORDER BY minute,setup').fetchall();db.close()
            self.assertEqual(before,after)
            self.assertFalse(result['LIVE_SIGNAL_READY'])

if __name__=='__main__':unittest.main()
