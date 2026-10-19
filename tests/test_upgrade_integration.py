import asyncio,json,os,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from core.storage import Store
from data.providers import UnconfiguredProvider
from core.upgrade_service import Engine
from data.stream import Stream,encode
from risk.options_policy import check
class IntegrationTests(unittest.TestCase):
    def test_worker_uses_current_clock_after_collection(self):
        from core.signals import build as real_build
        from core.paper_service import tick as real_paper_tick
        from data.models import quote
        started=datetime(2026,10,8,15,tzinfo=timezone.utc)
        arrived=started+timedelta(seconds=10)
        class Clock(datetime):
            calls=0
            @classmethod
            def now(cls,tz=None):
                cls.calls+=1
                return started if cls.calls==1 else arrived
        evaluated=[];proxy_times=[];verify_times=[]
        def capture(*args,**kwargs):
            evaluated.append((args[3],args[7]))
            return real_build(*args,**kwargs)
        def paper_capture(*args,**kwargs):
            proxy_times.append(args[3])
            return real_paper_tick(*args,**kwargs)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'config').mkdir();(root/'monitoring').mkdir()
            from core.storage import ROOT
            (root/'config/upgrade.json').write_bytes((ROOT/'config/upgrade.json').read_bytes())
            store=Store(root/'runtime/aegis.sqlite')
            store.put('quote:SPY',quote('alpaca-sip','SPY',{'bp':99.99,'ap':100.01,'t':arrived.isoformat()},received=arrived.isoformat()).view(arrived))
            with patch('core.upgrade_service.ROOT',root),patch('core.upgrade_service.books',return_value={}),patch('core.upgrade_service.datetime',Clock),patch('core.upgrade_service.build',side_effect=capture),patch('core.paper_service.tick',side_effect=paper_capture),patch('ops.live_verify.scheduled',side_effect=lambda s,n,**kw:verify_times.append(n)):
                engine=Engine(store,UnconfiguredProvider())
                for key in ('news_headlines','market_news','reddit_sentiment','calendar'):engine.due[key]=float('inf')
                result=engine.tick()
            self.assertEqual(evaluated[0][0]['quality'],'DATA_OK')
            self.assertEqual(evaluated[0][0]['freshness_seconds'],0)
            self.assertEqual(evaluated[0][1],arrived)
            self.assertEqual(proxy_times,[arrived]);self.assertEqual(verify_times,[arrived])
            self.assertEqual(result['action'],'NO TRADE')
            self.assertFalse(store.get('latest_evaluation')['live_signal_ready'])
            engine.close()
    def test_atomic_outbox_and_duplicate(self):
        from core.upgrade_service import enqueue
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'monitoring').mkdir();store=Store(root/'runtime.sqlite')
            with patch('core.upgrade_service.ROOT',root):
                enqueue(store,'fixture-alert','test message');original=(root/'monitoring/outbox/fixture-alert.json').read_text();enqueue(store,'fixture-alert','changed message')
            self.assertEqual((root/'monitoring/outbox/fixture-alert.json').read_text(),original);self.assertFalse(list((root/'monitoring/outbox').glob('*.pending')));store.close()
    def test_worker_missing_dependencies_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'config').mkdir();(root/'monitoring').mkdir()
            from core.storage import ROOT
            (root/'config/upgrade.json').write_bytes((ROOT/'config/upgrade.json').read_bytes())
            store=Store(root/'runtime/aegis.sqlite')
            with patch('core.upgrade_service.ROOT',root),patch('core.upgrade_service.books',return_value={}),patch('news.market_outlook.RSSProvider.fetch',return_value=b'<rss/>'):
                engine=Engine(store,UnconfiguredProvider());result=engine.tick()
            self.assertEqual(result['action'],'NO TRADE');self.assertEqual(store.get('worker_health')['state'],'RUNNING');self.assertFalse(store.events('signal')[0]['actionable']);self.assertEqual(store.get('news')['quality'],'DATA_INCOMPLETE');engine.close()
    def test_stream_auth_failure_reconnect_is_sanitized(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(Path(d)/'runtime.sqlite');stream=Stream(store)
            class Socket:
                async def __aenter__(self):return self
                async def __aexit__(self,*a):pass
                async def recv(self):return json.dumps([{'T':'error','msg':'secret must not be logged'}])
                async def send(self,message):pass
            stream.connect=lambda *a,**k:Socket();delays=[]
            async def wait(seconds):delays.append(seconds);stream.stop.set()
            stream.wait=wait
            with patch.dict(os.environ,{'APCA_API_KEY_ID':'fixture','APCA_API_SECRET_KEY':'fixture'}):asyncio.run(stream.run())
            self.assertGreaterEqual(delays[0],300);self.assertEqual(store.get('stream:sip')['state'],'STOPPED')
            rows=store.db.execute('SELECT payload FROM audit').fetchall();self.assertNotIn('secret',str(rows));self.assertEqual(len(rows),1);store.close()
    def test_risk_limits_and_breaker(self):
        now=datetime(2026,10,5,15,tzinfo=timezone.utc);policy={'max_trade_premium_usd':100,'max_exposure_usd':200,'max_daily_loss_usd':50,'max_consecutive_losses':3,'daily_reconciled_date':'2026-10-05','daily_loss_usd':50,'consecutive_losses':3}
        r=check(policy,[{'quantity':1,'cost_usd':'150'}],premium=80,now=now);self.assertFalse(r['ready']);self.assertIn('DAILY_CIRCUIT_BREAKER',r['reasons']);self.assertIn('LOSS_STREAK_COOLDOWN',r['reasons']);self.assertIn('PROJECTED_EXPOSURE_LIMIT',r['reasons'])
if __name__=='__main__':unittest.main()
