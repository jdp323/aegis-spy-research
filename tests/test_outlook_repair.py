"""Reported overnight failures and approved configuration boundaries; offline only."""
import json
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode

from core.storage import Store
from news.market_outlook import language, build, text_for
from monitoring.premarket_brief import saved_text, command_text
from data.local_setup import SetupServer, parse_reddit
from news import reddit

OVERNIGHT = datetime(2026, 10, 9, 7, 46, tzinfo=timezone.utc)
REDDIT_CONFIG = {'client_id': 'syntheticid', 'client_secret': 'syntheticsecret',
                 'refresh_token': 'syntheticrefresh',
                 'user_agent': 'windows:AEGIS:1.0 (by /u/fixture_user)', 'access_approved': True}
REDDIT_FIELDS = {'REDDIT_CLIENT_ID': 'syntheticid', 'REDDIT_CLIENT_SECRET': 'syntheticsecret',
                 'REDDIT_REFRESH_TOKEN': 'syntheticrefresh', 'REDDIT_USER_AGENT': REDDIT_CONFIG['user_agent'],
                 'REDDIT_ACCESS_APPROVED': 'yes'}

class ReactionTests(unittest.TestCase):
    def test_reported_dalio_headline_is_not_a_stock_price_rise(self):
        r = language("Ray Dalio warns the stock market's cushion against higher rates is shrinking")
        self.assertEqual(r['direction'], 'NEUTRAL')
        self.assertIn('valuation pressure', r['reason'])

    def test_reactions_belong_to_the_market_subject(self):
        for text in ('Stocks face pressure as Treasury yields rise', 'Stock market braces for lower interest rates',
                     'Stocks watch bond yields fall', 'SPY outlook: stocks await a rally in bond prices'):
            self.assertEqual(language(text)['direction'], 'NEUTRAL', text)
        for text, expected in (('Stocks close sharply higher as Treasury yields fall', 'UP'),
                               ('SPY shares fall as interest rates rise', 'DOWN'),
                               ('Stocks rise but futures fall', 'NEUTRAL'),
                               ('Stocks could rally', 'NEUTRAL')):
            self.assertEqual(language(text)['direction'], expected, text)

class OvernightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / 'fixture.sqlite')
        self.addCleanup(self.store.close)

    def test_closed_outlook_explains_next_open_without_inventing_a_bias(self):
        with patch('news.market_outlook.market_evidence', return_value={'bias':'UNAVAILABLE','mode':'NO CURRENT PRICE','reason':'OUTSIDE_REGULAR_SESSION'}):
            r = build(self.store, OVERNIGHT)
        text = text_for(r)
        self.assertIn('SESSION: CLOSED', text)
        self.assertIn('2026-10-09 09:30 ET', text)
        self.assertIn('morning outlook: 09:15 ET', text)
        self.assertIn('cannot confirm', text)
        self.assertEqual(r['market']['bias'], 'UNAVAILABLE')
        self.assertFalse(r['validated_prediction'])

    def test_active_session_missing_data_is_not_called_closed(self):
        at = OVERNIGHT.replace(hour=15)
        with patch('news.market_outlook.market_evidence', return_value={'bias':'UNAVAILABLE','mode':'NO CURRENT PRICE','reason':'STALE_QUOTE'}):
            text = text_for(build(self.store, at))
        self.assertIn('Price inputs not ready: STALE_QUOTE', text)
        self.assertNotIn('regular-session trend is not running', text)

    def test_0346_report_is_not_due_yet_and_never_fetches(self):
        text = command_text(self.store, OVERNIGHT, refresh=lambda **kw:self.fail('No premarket fetch before 04:00'))
        self.assertIn('NOT DUE YET', text)
        self.assertIn('Fri 2026-10-09 09:15 ET', text)
        self.assertNotIn('REPORT MISSING', text)
        self.assertIsNone(self.store.get('premarket_report:2026-10-09'))

    def test_weekend_and_unknown_calendar_do_not_invent_schedules(self):
        weekend = OVERNIGHT + timedelta(days=1)
        text = saved_text(self.store, weekend)
        self.assertIn('NO REPORT DUE TODAY', text)
        self.assertIn('Mon 2026-10-12 09:15 ET', text)
        text = saved_text(self.store, datetime(2028,1,4,8,tzinfo=timezone.utc))
        self.assertIn('exchange calendar needs refresh', text)

    def test_dst_uses_local_0915_and_late_report_shows_failure(self):
        winter = datetime(2026,11,27,12,tzinfo=timezone.utc)
        self.assertIn('Fri 2026-11-27 09:15 ET', saved_text(self.store,winter))
        self.assertIn('REPORT MISSING', saved_text(self.store, OVERNIGHT.replace(hour=14)))

    def test_early_premarket_warmup_has_no_network(self):
        text = command_text(self.store, OVERNIGHT.replace(hour=8,minute=15), refresh=lambda **kw:self.fail('No warmup fetch'))
        self.assertIn('not before 04:30 ET', text)

    def test_preview_is_separate_and_uses_verified_completed_public_bars(self):
        from data.premarket_spy import URL
        at = OVERNIGHT.replace(hour=9, minute=0) # 05:00 EDT
        start = at - timedelta(hours=1)
        rows = [{'timestamp':int((start+timedelta(minutes=5*i)).timestamp()),
                 'open':600,'high':600.2,'low':599.8,'close':600.1,'volume':100} for i in range(12)]
        raw = {'source':URL,'symbol':'SPY','use':'DELAY_UNVERIFIED_RESEARCH_ONLY',
               'status':'RESEARCH_DATA_RECEIVED','fetched_at':at.isoformat(),'sha256':'a'*64,'bars':rows}
        with patch('monitoring.premarket_brief.verified',return_value=True),patch('research.live_trend.evaluate',return_value={'status':'UNAVAILABLE','reason':'CLOSED'}):
            text = command_text(self.store, at, refresh=lambda **kw:raw)
        self.assertIn('ON-DEMAND PREMARKET DRAFT', text)
        self.assertIn('2026-10-09 05:00 ET', text)
        self.assertIn('DELAY UNVERIFIED', text)
        self.assertIn('still due at 09:15 ET', text)
        self.assertIsNone(self.store.get('premarket_report:2026-10-09'))
        self.assertEqual(self.store.db.execute('select count(*) from events').fetchone()[0],0)

    def test_bad_preview_never_supplies_prices_or_a_direction(self):
        at = OVERNIGHT.replace(hour=9, minute=0)
        text = command_text(self.store,at,refresh=lambda **kw:{'status':'UNAVAILABLE','bars':[]})
        self.assertIn('DRAFT: UNAVAILABLE',text)
        self.assertIn('No direction or price invented',text)
        self.assertNotIn('$',text)

    def test_saved_report_does_not_refresh_or_become_a_current_trend(self):
        self.store.put('premarket_report:2026-10-09',{'message':'stored fixture'})
        text = command_text(self.store,OVERNIGHT,refresh=lambda **kw:self.fail('Saved report does not fetch'))
        self.assertIn('SAVED 09:15 OUTLOOK',text)
        self.assertIn('not current-price',text)

    def test_real_refresh_uses_post_fetch_clock_not_pre_fetch_time(self):
        from data.premarket_spy import URL
        at=OVERNIGHT.replace(hour=9,minute=0)
        received=at+timedelta(seconds=4)
        rows=[{'timestamp':int((at-timedelta(hours=1)+timedelta(minutes=5*i)).timestamp()),
               'open':600,'high':600.2,'low':599.8,'close':600.1,'volume':100} for i in range(12)]
        raw={'source':URL,'symbol':'SPY','use':'DELAY_UNVERIFIED_RESEARCH_ONLY','status':'RESEARCH_DATA_RECEIVED',
             'fetched_at':received.isoformat(),'sha256':'a'*64,'bars':rows}
        with patch('monitoring.premarket_brief.datetime',wraps=datetime) as clock,patch('data.trend_spy.refresh',return_value=raw),patch('monitoring.premarket_brief.verified',return_value=True),patch('research.live_trend.evaluate',return_value={'status':'UNAVAILABLE','reason':'CLOSED'}):
            clock.now.return_value=received
            text=command_text(self.store,at)
        self.assertIn('ON-DEMAND PREMARKET DRAFT',text)
        self.assertNotIn('DRAFT: UNAVAILABLE',text)

    def test_calendar_risk_uses_same_seven_day_freshness_and_date_only_label(self):
        from monitoring.premarket_brief import build as prebuild, text_for as pretext
        from tests.test_premarket_brief import fixture, NOW
        news={'quality':'DATA_OK','risk':'MODERATE','stale':False,'verified_at':(NOW-timedelta(days=1)).isoformat(),
              'events':[{'type':'PPI','time_utc':(NOW+timedelta(minutes=15)).isoformat(),'time_source':'DATE_ONLY'}]}
        with patch('monitoring.premarket_brief.verified',return_value=True):
            report=prebuild(fixture(),news,NOW)
            self.assertEqual(report['news'],'MODERATE')
            self.assertIn('CONFIGURED EVENT: PPI',pretext(report))
            self.assertIn('release time unavailable',pretext(report))
            self.assertNotIn('PPI 2026-10-06 09:30',pretext(report))
            news['verified_at']=(NOW-timedelta(days=8)).isoformat()
            self.assertEqual(prebuild(fixture(),news,NOW)['news'],'UNAVAILABLE')

class ApprovedSetupTests(unittest.TestCase):
    def test_parse_requires_explicit_approval_all_fields_and_no_duplicates(self):
        valid = {k:[v] for k,v in REDDIT_FIELDS.items()}
        self.assertEqual(parse_reddit(valid),REDDIT_CONFIG)
        for changed in ({k:v for k,v in valid.items() if k!='REDDIT_ACCESS_APPROVED'},
                        {**valid,'REDDIT_ACCESS_APPROVED':['no']},
                        {**valid,'REDDIT_CLIENT_ID':['first','second']},
                        {**valid,'OTHER':['extra']}, {**valid,'REDDIT_REFRESH_TOKEN':['short']}):
            with self.assertRaises(ValueError):parse_reddit(changed)

    def test_reddit_save_roundtrip_and_existing_config_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'reddit.dpapi'
            raw = json.dumps(REDDIT_CONFIG).encode()
            with patch.object(reddit,'PRIVATE',path),patch('monitoring.vault.transform',side_effect=[b'encrypted',raw]):
                reddit.save(REDDIT_CONFIG)
                self.assertEqual(path.read_bytes(),b'encrypted')
                with self.assertRaises(RuntimeError):reddit.save(REDDIT_CONFIG)

    def test_reddit_save_does_not_write_plaintext_or_failed_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'reddit.dpapi'
            with patch.object(reddit,'PRIVATE',path),patch('monitoring.vault.transform',side_effect=[b'encrypted',b'invalid']):
                with self.assertRaises(RuntimeError):reddit.save(REDDIT_CONFIG)
                self.assertFalse(path.exists())

    def test_local_form_requires_approval_exact_origin_and_single_use(self):
        server=SetupServer(('127.0.0.1',0))
        thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.01},daemon=True)
        thread.start();host='127.0.0.1:'+str(server.server_port)
        def send(fields,origin='http://'+host):
            c=HTTPConnection('127.0.0.1',server.server_port,timeout=2)
            c.request('POST','/setup/'+server.token,body=urlencode(fields),headers={'Content-Type':'application/x-www-form-urlencoded','Origin':origin})
            r=c.getresponse();status=r.status;body=r.read().decode();c.close();return status,body
        try:
            with patch('news.reddit.save') as save:
                self.assertEqual(send(REDDIT_FIELDS,'http://evil.example')[0],403)
                self.assertEqual(send({k:v for k,v in REDDIT_FIELDS.items() if k!='REDDIT_ACCESS_APPROVED'})[0],400)
                save.assert_not_called();self.assertFalse(server.used)
                status,body=send(REDDIT_FIELDS)
                self.assertEqual(status,200);self.assertIn('verify OAuth read access',body)
                self.assertNotIn('syntheticsecret',body);save.assert_called_once_with(REDDIT_CONFIG)
                self.assertEqual(send(REDDIT_FIELDS)[0],410)
        finally:
            server.shutdown();server.server_close();thread.join(timeout=2)

    def test_missing_sentiment_explains_dependency_without_neutral_placeholder(self):
        text=reddit.text_for(None,OVERNIGHT)
        self.assertIn('Reddit-approved Data API access',text)
        self.assertIn('website login alone',text)
        self.assertIn('SENTIMENT: UNAVAILABLE',text)

if __name__=='__main__':unittest.main()
