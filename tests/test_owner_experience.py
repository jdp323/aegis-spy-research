import unittest,tempfile,json,copy,sqlite3
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from core.sessions import ET
from core.directional_research import view,record,resolve,VERSION
from core.research_pause import advance
from core.storage import Store
from monitoring.owner_messages import status_text,premarket_text,idea_text,update_text,recap_text,verified_option
from ops.day_simulation import MemoryStore,config,inputs
from core.idea_service import tick,context
from backtesting.idea_tracker import IdeaTracker
from strategies.published_baselines import concretum_signal,opening_range,first_last

NOW=datetime(2026,10,21,11,0,tzinfo=ET).astimezone(timezone.utc)
def ctx(flat=False):
    start=NOW.timestamp()-31*60
    bars=[dict(timestamp=start+n*60,open=500,high=500.05 if flat else 503,low=499.95 if flat else 499,close=500 if flat else 500+n*.01,volume=100) for n in range(31)]
    return dict(reason='data not fresh',feed_quality='IEX',bar_research=dict(reason=None,quality='COMPLETED_BAR_RESEARCH_ONLY',bars=bars,features={'1m':{'vwap_approx':500,'atr14':.1}},feed_quality='IEX',last_completed_close=bars[-1]['close'],source_timestamp=NOW.isoformat()))
def idea():return dict(signal_id='EXAMPLE',timestamp=NOW.isoformat(),direction='CALL',trigger=500.1,do_not_chase=500.8,invalidation=499.8,t2=501.2,signal_expiry=(NOW+timedelta(minutes=10)).isoformat(),max_hold_until=(NOW+timedelta(minutes=60)).isoformat(),entry_condition='a completed 1-minute close above SPY $500.10')
def closed(i,minute,loss=True):return dict(signal_id=str(i),status='CLOSED',closed_at=(NOW+timedelta(minutes=minute)).isoformat(),r_multiple=-1 if loss else 1,alerted=False)

class Experience(unittest.TestCase):
    def test_available_trend_is_independent_of_option_and_quote(self):
        c=ctx();r=view(c,NOW);self.assertEqual(r['trend'],'UP')
        text=status_text(c,NOW,{'quality':'DATA_OK','risk':'NORMAL'})
        self.assertEqual(len(text.splitlines()),5);self.assertIn('Last completed-bar trend: UP',text);self.assertIn('Next hour: unavailable',text);self.assertIn('WAIT',text);self.assertNotIn('SOURCE_',text)
    def test_retained_oct20_delay_cannot_be_refreshed_by_heartbeat(self):
        # Original retained source/receipt times; positive prices below are
        # synthetic schema placeholders, not reconstructed market prices.
        from data.models import quote
        from data.reliability import quote_diagnostics
        source='2026-10-20T19:59:53.012Z';receipt='2026-10-20T20:00:08.006Z';now=datetime.fromisoformat(receipt.replace('Z','+00:00'))
        q=quote('alpaca-iex','SPY',{'bp':500,'ap':500.02,'t':source},received=receipt).view(now)
        d=quote_diagnostics(q,now,'alpaca-iex');self.assertEqual(d['predicate'],'SOURCE_TOO_OLD');self.assertAlmostEqual(d['source_age_seconds'],14.994,places=3);self.assertEqual(d['receipt_age_seconds'],0)
    def test_sideways_is_not_missing(self):
        self.assertEqual(view(ctx(True),NOW)['trend'],'SIDEWAYS')
        self.assertEqual(view({},NOW)['trend'],'DATA UNAVAILABLE')
    def test_future_or_gapped_or_old_bars_never_show_trend(self):
        for shift in (60,-180):
            c=ctx();c['bar_research']['bars'][-1]['timestamp']+=shift
            self.assertEqual(view(c,NOW)['trend'],'DATA UNAVAILABLE')
    def test_future_horizons_do_not_stretch_to_close(self):
        late=NOW.astimezone(ET).replace(hour=15,minute=30).astimezone(timezone.utc);c=ctx()
        for b in c['bar_research']['bars']:b['timestamp']+=(late-NOW).total_seconds()
        r=view(c,late);self.assertEqual(r['outlooks']['H60']['bias'],'ABSTAIN');self.assertEqual(r['outlooks']['H120']['bias'],'ABSTAIN');self.assertEqual(r['outlooks']['SESSION']['bias'],'UP')
    def test_forecast_immutable_exact_future_only_missing_is_retained(self):
        s=MemoryStore();r=view(ctx(),NOW);record(s,'one',NOW,r,'H60');record(s,'one',NOW,{},'H60')
        self.assertEqual(s.events('directional_forecast')[0]['bias'],'UP')
        resolve(s,[],NOW+timedelta(minutes=59));self.assertFalse(s.events('directional_forecast_outcome'))
        resolve(s,[],NOW+timedelta(minutes=60,seconds=6));self.assertEqual(s.events('directional_forecast_outcome')[0]['status'],'MISSING_OUTCOME')
        resolve(s,[],NOW+timedelta(hours=2));self.assertEqual(len(s.events('directional_forecast_outcome')),1)
    def test_premarket_outcome_open_to_close_not_premarket_price(self):
        s=MemoryStore();end=NOW.astimezone(ET).replace(hour=16).astimezone(timezone.utc)
        record(s,'pre',NOW-timedelta(hours=2),{'outlooks':{'PREMARKET':{'bias':'UP','reference':999,'target_at':end.isoformat()}}},'PREMARKET',True)
        opening=end.astimezone(ET).replace(hour=9,minute=30).timestamp();rows=[dict(timestamp=opening,open=500,close=500),dict(timestamp=end.timestamp()-60,close=501)]
        resolve(s,rows,end);o=s.events('directional_forecast_outcome')[0];self.assertEqual(o['reference'],500);self.assertTrue(o['correct'])
    def test_premarket_seven_lines_no_fabricated_levels(self):
        text=premarket_text({}, {}, NOW);self.assertEqual(len(text.splitlines()),8);self.assertIn('Opening-hour lean: UNCLEAR',text);self.assertIn('DATA UNAVAILABLE',text);self.assertNotIn('$',text)
    def test_watch_idea_nine_lines_actual_confirmation_and_expiry(self):
        i=idea();text=idea_text(i,{},{});self.assertEqual(len(text.splitlines()),9);self.assertIn('1-minute',text);self.assertIn('Underlying watch only',text);self.assertIn('SPY target: $501.20',text)
        self.assertNotIn('BUY',text);i['signal_expiry']=i['max_hold_until'];self.assertIn('cancelled',idea_text(i,{},{}))
    def test_followup_only_change_and_id_not_actual_fill(self):
        for c in ('TARGET_2_HIT','STOP_HIT','TIME_EXIT','MONITORING_UNAVAILABLE','IDEA_CANCELLED'):
            t=update_text(idea(),c);self.assertIn('EXAMPLE',t);self.assertLessEqual(len(t.splitlines()),2);self.assertNotIn('you sold',t.lower())
    def test_recap_six_lines_no_rejection_dump(self):
        r=dict(idea(),alerted=False,status='CLOSED');t=recap_text([r],NOW,'UNAVAILABLE');self.assertEqual(len(t.splitlines()),8);self.assertIn('Ideas alerted: 0',t);self.assertIn('Forward outlook: outcomes unavailable',t);self.assertNotIn('structure',t)
    def test_pause_consumes_silent_losses_once_and_restart(self):
        rows=[closed(n,n) for n in range(3)];s,active,w=advance(None,rows,NOW+timedelta(minutes=3));self.assertTrue(active);self.assertEqual(len(w),1)
        first=copy.deepcopy(s);s,active,w=advance(json.loads(json.dumps(s)),rows+[closed(3,10)],NOW+timedelta(minutes=11));self.assertEqual(s['episode']['end'],first['episode']['end']);self.assertFalse(w)
        s,active,w=advance(s,rows+[closed(3,10)],NOW+timedelta(minutes=63));self.assertFalse(active);self.assertFalse(w)
    def test_new_episode_requires_three_new_post_pause_losses(self):
        s,_,_=advance(None,[closed(n,n) for n in range(3)],NOW+timedelta(minutes=3))
        old=s['episode']['id'];rows=[closed(4,63),closed(5,64),closed(6,65)]
        s,on,w=advance(s,rows,NOW+timedelta(minutes=66));self.assertTrue(on);self.assertNotEqual(old,s['episode']['id']);self.assertEqual(len(w),1)
    def test_future_closures_do_not_pause_and_preview_pure(self):
        s,on,w=advance(None,[closed(1,1)],NOW);self.assertFalse(on);self.assertEqual(s['seen'],[])
    def test_merge_parsing_does_not_hold_write_lock_and_no_loss(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'db.sqlite';a=Store(p);b=Store(p,lock_timeout=0);row={'t':'2026-10-20T14:00:00Z','c':1};a.put('bars',[row]);actual=__import__('data.models',fromlist=['stamp']).stamp;calls=[]
            def hook(v):
                if not calls:b.put('other',{'ok':True});calls.append(True)
                return actual(v)
            with patch('data.models.stamp',side_effect=hook):a.merge_rows('bars',[dict(row,t='2026-10-20T14:01:00Z')])
            self.assertEqual(len(a.get('bars')),2);self.assertTrue(b.get('other')['ok']);a.close();b.close()
    def test_put_many_is_atomic_and_does_not_omit_quote(self):
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d)/'db.sqlite');s.put_many({'q':{'source':'old'},'h':{'at':'now'}});self.assertEqual(s.metrics['transactions'],1);self.assertEqual(s.get('q')['source'],'old');s.close()
    def test_stream_future_sample_uses_same_feed_and_no_pre_target_quote(self):
        from core.directional_research import capture_future_quote
        from data.models import quote
        s=MemoryStore();r=view(ctx(),NOW);record(s,'future',NOW,r,'H60');end=NOW+timedelta(minutes=60)
        def q(at,feed='iex'):return quote('alpaca-'+feed,'SPY',{'bp':501,'ap':501.02,'t':at.isoformat()},received=at.isoformat()).view(at)
        capture_future_quote(s,q(end-timedelta(seconds=1)),end-timedelta(seconds=1));self.assertFalse(s.events('directional_forecast_outcome'))
        capture_future_quote(s,q(end,'sip'),end);self.assertFalse(s.events('directional_forecast_outcome'))
        capture_future_quote(s,q(end+timedelta(seconds=1)),end+timedelta(seconds=1));o=s.events('directional_forecast_outcome');self.assertEqual(len(o),1);self.assertTrue(o[0]['correct'])
        capture_future_quote(s,q(end+timedelta(seconds=2)),end+timedelta(seconds=2));self.assertEqual(len(s.events('directional_forecast_outcome')),1)
    def test_telemetry_connection_is_closed_by_owning_store(self):
        from data.stream import Stream
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d)/'a.sqlite');stream=Stream(s,feed='iex');stream.log('CONNECT');s.close()
            with self.assertRaises(sqlite3.ProgrammingError):stream._events.db.execute('SELECT 1')
    def test_corporate_action_pages_and_missing_schema_fail_closed(self):
        from data.corporate_actions import collect
        class Provider:
            def __init__(self):self.calls=[]
            def get(self,path,params):
                self.calls.append((path,params));return {'corporate_actions':{'cash_dividends':[{'symbol':'SPY','ex_date':'2026-10-20','rate':1.2}]}}
        p=Provider();r=collect(p,'2026-10-19','2026-10-20');self.assertEqual(r['dividends']['2026-10-20'],1.2);self.assertNotIn('2026-10-19',r['dividends']);self.assertFalse(r['ex_date_coverage_verified']);self.assertEqual(p.calls[0][0],'/v1/corporate-actions')
        p.get=lambda *args:{}
        with self.assertRaisesRegex(ValueError,'SCHEMA'):collect(p,'2026-10-19','2026-10-20')
        with self.assertRaisesRegex(ValueError,'RANGE'):collect(p,'2025-01-01','2026-10-20')
    def test_cas_merge_rebuilds_after_concurrent_same_key_update(self):
        with tempfile.TemporaryDirectory() as d:
            a=Store(Path(d)/'a.sqlite');b=Store(a.path);row={'t':'2026-10-20T14:00:00Z'};a.put('bars',[row]);actual=__import__('data.models',fromlist=['stamp']).stamp;hit=[]
            def hook(value):
                if not hit:
                    hit.append(True);b.put('bars',[row,{'t':'2026-10-20T14:01:00Z'}])
                return actual(value)
            with patch('data.models.stamp',side_effect=hook):a.merge_rows('bars',[{'t':'2026-10-20T14:02:00Z'}])
            self.assertEqual(len(a.get('bars')),3);self.assertEqual(a.metrics['merge_conflicts'],1);a.close();b.close()
    def test_recorder_fingerprint_preserves_future_completion_and_revisions(self):
        from data.session_recorder import Recorder
        with tempfile.TemporaryDirectory() as d:
            r=Recorder(Path(d)/'h.sqlite');raw=[{'t':NOW.isoformat(),'o':500,'h':501,'l':499,'c':500,'v':100}]
            self.assertEqual(r.bars(raw,'IEX',NOW),0)
            self.assertEqual(r.bars(raw,'IEX',NOW+timedelta(minutes=1)),1)
            before=r.db.execute('SELECT recorded_at FROM session_bars').fetchone()[0]
            self.assertEqual(r.bars(raw,'IEX',NOW+timedelta(minutes=2)),0)
            self.assertEqual(r.db.execute('SELECT recorded_at FROM session_bars').fetchone()[0],before)
            self.assertEqual(r.bars([dict(raw[0],c=500.1)],'IEX',NOW+timedelta(minutes=2)),1);r.close()
    def test_trace_revisions_preserve_first_snapshot_and_refuse_mutation(self):
        from core.rejection_trace import persist
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'o.sqlite';a={'setup':'VWAP_RECLAIM','direction':'CALL','engine_version':'fixture','at':NOW.isoformat(),'blocker':'SOURCE_TOO_OLD'}
            persist(p,[a],NOW);persist(p,[dict(a,blocker=None)],NOW);db=sqlite3.connect(p)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM rejection_trace_revisions').fetchone()[0],2)
            self.assertEqual(json.loads(db.execute('SELECT payload FROM rejection_traces').fetchone()[0])['blocker'],'SOURCE_TOO_OLD')
            with self.assertRaises(sqlite3.IntegrityError):db.execute('DELETE FROM rejection_trace_revisions')
            db.close()
    def test_compact_packet_preserves_manifest_and_scans_before_omission(self):
        from ops.verification_packet import compact
        manifest=[{'path':str(n),'sha256':'a'*64} for n in range(100)]
        p=compact({'change_manifest':manifest,'old_excerpt':'x'*3000})
        self.assertEqual(p['change_manifest'],manifest);self.assertIn('sha256',p['old_excerpt'])
        from ops.verification_packet import write
        with tempfile.TemporaryDirectory() as d:
            saved=write(p,d).with_suffix('.json');self.assertEqual(json.loads(saved.read_text(encoding='utf-8'))['change_manifest'],manifest)
            self.assertEqual(len(saved.read_text(encoding='utf-8').splitlines()),1)
        with self.assertRaisesRegex(ValueError,'SECRET'):
            compact({'old_excerpt':'x'*2000+' 987654321:'+('a'*32)})
    def test_published_baselines_missing_inputs_refuse(self):
        self.assertEqual(concretum_signal([],[],None,None)['status'],'UNAVAILABLE');self.assertEqual(first_last([],500)['status'],'UNAVAILABLE');self.assertEqual(opening_range([])['status'],'UNAVAILABLE')
    def test_concretum_uses_prior_same_clock_only_and_fixed_cadence(self):
        c=ctx();bars=c['bar_research']['bars'][:30];past=[]
        for n in range(14):past.append([dict(b,timestamp=b['timestamp']-(n+1)*86400) for b in bars])
        r=concretum_signal(bars,past,500,0);self.assertEqual(r['status'],'RESEARCH');self.assertEqual(concretum_signal(bars[:-1],past,500,0)['status'],'ABSTAIN')
    def test_full_day_uses_actual_dispatch_fake_outbox_and_preserves_source(self):
        from ops.day_simulation import run_scenario
        r=run_scenario('normal',NOW.astimezone(ET).date());self.assertTrue(r['PASS'])
        for e in r['timeline']:
            cap={'PREOPEN':8,'TREND_LINE':6,'SPY_IDEA':9,'RECAP':8}.get(e['alert_type'])
            if cap:self.assertLessEqual(len(e['text'].splitlines()),cap,e['alert_type'])
            if e['alert_type']=='TREND_LINE':self.assertTrue('Current trend:' in e['text'] or 'Last completed-bar trend:' in e['text'])

if __name__=='__main__':unittest.main()
