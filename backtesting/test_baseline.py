import unittest
from datetime import date, timedelta
from baseline import simulate, signal

class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.dates = [(date(2020,1,1)+timedelta(days=i)).isoformat() for i in range(260)]

    def test_signal_cannot_observe_future(self):
        p = [100.0]*260
        before = signal(p, 252, 'momentum_252')
        p[253:] = [1000.0]*7
        self.assertEqual(before, signal(p, 252, 'momentum_252'))

    def test_shock_does_not_create_its_own_exposure(self):
        p = [100.0]*260
        p[254] = 200.0
        r = simulate(self.dates, p, 'trend_200', 0, self.dates[254], self.dates[254])
        self.assertEqual(r['total_return'], 0.0)

    def test_entry_and_exit_costs(self):
        p = [100.0]*260
        r = simulate(self.dates, p, 'buy_hold', 10, self.dates[254], self.dates[-1])
        self.assertAlmostEqual(r['total_return'], .999**2-1)
        self.assertEqual(r['one_way_turnover'], 2)

    def test_previous_close_signal_waits_one_full_session(self):
        p = [100.0]*260
        p[253] = 200.0
        # The spike at t-1 cannot determine the position for return ending t.
        r = simulate(self.dates, p, 'trend_200', 0, self.dates[254], self.dates[254])
        self.assertEqual(r['average_exposure'], 0)
        self.assertEqual(r['total_return'], 0)

    def test_increasing_cost_reduces_same_path_wealth(self):
        p = [100+i for i in range(260)]
        low = simulate(self.dates, p, 'buy_hold', 5, self.dates[254], self.dates[-1])
        high = simulate(self.dates, p, 'buy_hold', 25, self.dates[254], self.dates[-1])
        self.assertLess(high['total_return'], low['total_return'])

    def test_cash_flat_and_zero_cost(self):
        r = simulate(self.dates, [100.0]*260, 'cash', 25, self.dates[254], self.dates[-1])
        self.assertEqual(r['total_return'], 0)
        self.assertEqual(r['one_way_turnover'], 0)

    def test_buy_hold_matches_endpoints(self):
        p = [100+i for i in range(260)]
        r = simulate(self.dates, p, 'buy_hold', 0, self.dates[254], self.dates[-1])
        self.assertAlmostEqual(r['total_return'], p[-1]/p[253]-1)

if __name__ == '__main__': unittest.main()
