import sqlite3
import tempfile
import unittest
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from accounting.cycles import CycleLedger, LedgerError


class CycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/'ledger.sqlite'
        self.ledger = CycleLedger(self.path)
        self.ledger.initialize('init', '51', verified=True)

    def close(self, cycle, terminal, gross, fees='0', **changes):
        args = dict(terminal_equity=terminal, gross_realized_pnl=gross, fees=fees,
                    reconciled=True, open_positions=0, open_orders=0)
        args.update(changes)
        return self.ledger.close_cycle('close-'+cycle, cycle, **args)

    def test_requested_two_profit_cycles(self):
        self.ledger.open_cycle('open-1', 'one')
        s = self.close('one', '80', '29')
        self.assertEqual((s['protectedreserve'], s['tradingcash']), ('51.00', '29.00'))
        self.ledger.open_cycle('open-2', 'two')
        s = self.close('two', '50', '21')
        self.assertEqual((s['protectedreserve'], s['tradingcash'], s['totalcash']), ('80.00', '21.00', '101.00'))

    def test_loss_does_not_refill_or_protect_prior_stake(self):
        self.ledger.open_cycle('open-1', 'one')
        self.close('one', '80', '29')
        self.ledger.open_cycle('open-2', 'two')
        s = self.close('two', '20', '-9')
        self.assertEqual((s['protectedreserve'], s['tradingcash']), ('51.00', '20.00'))

    def test_fees_deducted_exactly_once_and_breakeven(self):
        self.ledger.open_cycle('open-1', 'one')
        s = self.close('one', '80', '30', '1')
        self.assertEqual(s['tradingcash'], '29.00')
        self.ledger.open_cycle('open-2', 'two')
        s = self.close('two', '29', '1', '1')
        self.assertEqual((s['protectedreserve'], s['tradingcash']), ('51.00', '29.00'))

    def test_deposits_quarantined_and_withdrawals_bounded(self):
        self.ledger.open_cycle('open-1', 'one')
        self.ledger.external_cashflow('deposit', 'deposit', '100', verified=True)
        with self.assertRaises(LedgerError): self.close('one', '151', '0')
        self.close('one', '51', '0')
        s = self.ledger.external_cashflow('withdraw', 'withdrawal', '90', verified=True)
        self.assertEqual((s['tradingcash'], s['unallocatedcash'], s['totalcash']), ('51.00', '10.00', '61.00'))
        with self.assertRaises(LedgerError):
            self.ledger.external_cashflow('bad-withdraw', 'withdrawal', '11', verified=True)

    def test_partial_or_unreconciled_close_rejected_atomically(self):
        self.ledger.open_cycle('open-1', 'one')
        before = self.ledger.state()
        for changes in ({'open_positions':1}, {'open_orders':1}, {'reconciled':False}, {'open_positions':False}):
            with self.assertRaises(LedgerError): self.close('one', '80', '29', **changes)
        with self.assertRaises(LedgerError): self.close('one', '80', '30')
        self.assertEqual(self.ledger.state(), before)
        self.assertEqual(len(self.ledger.events()), 2)

    def test_restart_idempotency_and_mismatch(self):
        self.ledger.open_cycle('open-1', 'one')
        expected = self.close('one', '80', '29')
        self.ledger = CycleLedger(self.path)
        self.assertEqual(self.close('one', '80', '29'), expected)
        self.assertEqual(len(self.ledger.events()), 3)
        with self.assertRaises(LedgerError): self.close('one', '81', '30')
        with self.assertRaises(LedgerError): self.ledger.open_cycle('reopen', 'one')

    def test_decimal_precision_finite_and_no_leverage(self):
        for amount in ('NaN', 'Infinity', '1.001', '-1', '1e999999', 0.1):
            with self.assertRaises(LedgerError):
                self.ledger.external_cashflow('bad', 'deposit', amount, verified=True)
        self.ledger.open_cycle('open-1', 'one')
        with self.assertRaises(LedgerError): self.close('one', '-0.01', '-51.01')
        s = self.close('one', '0', '-51')
        self.assertEqual(s['tradingcash'], '0.00')
        with self.assertRaises(LedgerError): self.ledger.open_cycle('open-2', 'two')

    def test_sql_append_only(self):
        with closing(sqlite3.connect(self.path)) as con:
            with self.assertRaises(sqlite3.IntegrityError): con.execute('DELETE FROM cycle_events')
            with self.assertRaises(sqlite3.IntegrityError): con.execute("UPDATE cycle_events SET kind='bad'")

    def test_concurrent_duplicate_commits_once(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.ledger.external_cashflow('same-deposit', 'deposit', '1.01', verified=True), range(8)))
        self.assertEqual(len(self.ledger.events()), 2)
        self.assertTrue(all(r['unallocatedcash'] == '1.01' for r in results))


if __name__ == '__main__': unittest.main()
