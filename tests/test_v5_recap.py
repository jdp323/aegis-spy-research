import unittest
from datetime import datetime,timezone
from core.sessions import ET
from ops.day_simulation import MemoryStore,inputs
from core.idea_service import recap_levels

class RecapLevels(unittest.TestCase):
    def test_completed_bars_without_quote_and_simulated_real_rejection(self):
        now=datetime(2026,10,9,16,15,tzinfo=ET).astimezone(timezone.utc)
        store=MemoryStore();rows=inputs(store,now)
        store.put('stream_bars:SPY',rows[:390]);store.put('quote:SPY',{})
        self.assertIn('Completed-session references (SIMULATED, not live)',recap_levels(store,now,True))
        self.assertIn('UNAVAILABLE',recap_levels(store,now))
        store.put('stream_bars:SPY',rows[:389])
        self.assertIn('UNAVAILABLE',recap_levels(store,now,True))
    def test_early_close_dst_and_gap(self):
        now=datetime(2026,11,27,13,15,tzinfo=ET).astimezone(timezone.utc)
        store=MemoryStore();rows=inputs(store,now)
        store.put('stream_bars:SPY',rows[:210])
        self.assertIn('Completed-session references',recap_levels(store,now,True))
        store.put('stream_bars:SPY',rows[:50]+rows[51:210])
        self.assertIn('UNAVAILABLE',recap_levels(store,now,True))
