import unittest,copy
from datetime import datetime,timezone,timedelta
from core.sessions import ET,market_session
from core.research_horizons import deadline,from_snapshot,describe,candidates

class HorizonRules(unittest.TestCase):
    def at(self,day='2026-10-19',time='10:45'):return datetime.fromisoformat(day+'T'+time).replace(tzinfo=ET).astimezone(timezone.utc)
    def bars(self,now,n=75):
        start=now-timedelta(minutes=n)
        return [{'t':(start+timedelta(minutes=i)).isoformat(),'o':500+i*.01,'h':501+i*.01,'l':499+i*.01,'c':500.1+i*.01,'v':100} for i in range(n)]
    def test_descriptive_bars_do_not_need_or_grant_quote(self):
        now=self.at();rows=self.bars(now)
        r=from_snapshot({'research_stream_bars:SPY:iex':rows},now)
        self.assertIsNone(r['reason']);self.assertEqual('COMPLETED_BAR_RESEARCH_ONLY',r['quality'])
        self.assertFalse(r['entry_eligible']);self.assertNotIn('quote',r)
        self.assertEqual('IEX',r['feed_quality'])
        self.assertEqual('UNAVAILABLE',describe(r,now)['H120']['bias'])
    def test_missing_synthetic_and_future_bars_do_not_repair_genuine_tail(self):
        now=self.at();rows=self.bars(now,31);rows.pop(-10)
        snap={'research_stream_bars:SPY:iex':rows,'confirmed_minutes:iex':['irrelevant']}
        self.assertIn('31_GENUINE',from_snapshot(snap,now)['reason'])
        rows=self.bars(now,31);rows.append(dict(rows[-1],t=now.isoformat()))
        r=from_snapshot({'research_stream_bars:SPY:iex':rows},now)
        self.assertEqual(31,len(r['bars']))
        r=from_snapshot({'research_stream_bars:SPY:iex':rows},now+timedelta(minutes=4))
        self.assertIn('120_SECONDS',r['reason'])
    def test_frame_unavailability_is_not_neutral_vote(self):
        now=self.at();r={'reason':None,'features':{'15m':{'trend':'BULL'},'5m':{'trend':'BULL'},'30m':{'trend':'BULL'},'1h':{'trend':'UNAVAILABLE'}}}
        views=describe(r,now)
        self.assertEqual('UP',views['H60']['bias']);self.assertEqual('UNAVAILABLE',views['H120']['bias'])
    def test_deadline_full_horizon_early_close_dst_and_unknown_year(self):
        self.assertEqual('11:45',deadline(self.at(),'H60').astimezone(ET).strftime('%H:%M'))
        self.assertIsNotNone(deadline(self.at(time='13:55'),'H120'))
        self.assertIsNone(deadline(self.at(time='13:56'),'H120'))
        self.assertIsNone(deadline(self.at(time='15:26'),'SESSION'))
        self.assertEqual('12:55',deadline(self.at('2026-11-27','10:55'),'H120').astimezone(ET).strftime('%H:%M'))
        self.assertIsNone(deadline(self.at('2026-11-27','10:56'),'H120'))
        self.assertEqual(17,deadline(self.at('2026-11-02'),'H120').hour)
        self.assertFalse(market_session(self.at('2027-11-25'))['active'])
        self.assertEqual(780,market_session(self.at('2027-11-26'))['close_minute'])
        self.assertEqual('DATA_INVALID',market_session(self.at('2028-01-03'))['quality'])
        self.assertTrue(market_session(self.at('2027-12-31'))['active'])
    def fixture(self):
        now=self.at();raw=self.bars(now);bars=[]
        for b in raw:bars.append({'timestamp':datetime.fromisoformat(b['t']).timestamp(),**{long:b[short] for long,short in [('open','o'),('high','h'),('low','l'),('close','c'),('volume','v')]}})
        bars[-2].update(close=502);bars[-1].update(close=502.1,low=500.9,high=502.2,volume=150)
        f={'1m':{'vwap_approx':500,'atr14':1},'opening_range':{'high':501,'low':499}}
        f.update({frame:{'trend':'BULL','atr14':2} for frame in ('5m','15m','30m','1h','daily')})
        return now,{'reason':None,'features':f,'bars':bars,'feed_quality':'IEX','provider':'alpaca-iex'}, {'payload':{'mid':502.1,'bid':502.09,'ask':502.11},'source_timestamp':now.isoformat()}
    def test_separate_grid_variants_and_immutable_price_names(self):
        now,ctx,q=self.fixture();rows=candidates(ctx,q,now)
        orb=[r for r in rows if r['setup_type']=='ORB_RETEST']
        self.assertEqual(6,len(orb));self.assertEqual(6,len({r['signal_id'] for r in orb}))
        for r in orb:
            self.assertEqual(501,r['trigger_level']);self.assertEqual(502.1,r['reference_midpoint'])
            self.assertAlmostEqual(502.12,r['modeled_entry_fill']);self.assertIsNone(r['actual_reported_fill'])
            self.assertLessEqual(datetime.fromisoformat(r['signal_expiry']),datetime.fromisoformat(r['max_hold_until']))
            self.assertFalse(r['live_signal_ready']);self.assertEqual(2,r['risk_reward'])
        offline=candidates(ctx,None,now,reference_price=502.1)
        self.assertTrue(offline);self.assertTrue(all(r['modeled_entry_fill'] is None and r['market_timestamp'] is None for r in offline))
        ctx['bars'][-1]['volume']=1;self.assertFalse(candidates(ctx,q,now))

if __name__=='__main__':unittest.main()
