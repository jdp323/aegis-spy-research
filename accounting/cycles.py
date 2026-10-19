"""Protected-profit cash ledger; manual reconciled settlements, never broker actions."""
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path


class LedgerError(ValueError):
    pass


def cents(value, signed=False):
    if isinstance(value, (bool, float)):
        raise LedgerError('Use decimal strings, integers, or Decimal; floats are not accepted')
    try:
        amount = Decimal(value)
        if not amount.is_finite() or amount.as_tuple().exponent < -2:
            raise LedgerError('Amount must be finite with at most two decimal places')
        if not signed and amount < 0:
            raise LedgerError('Negative cash is prohibited')
        if abs(amount) > Decimal('10000000000000'):
            raise LedgerError('Amount exceeds supported ledger range')
        result = int(amount * 100)
        return result
    except (InvalidOperation, TypeError, OverflowError) as exc:
        raise LedgerError('Invalid decimal amount') from exc


def money(value):
    return format(Decimal(value) / 100, '.2f')


class CycleLedger:
    """An account-specific, append-only SQLite journal. All API cash amounts are strings."""
    def __init__(self, path):
        self.path = str(path)
        if self.path == ':memory:':
            raise LedgerError('A durable filesystem database path is required')
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as con:
            con.executescript('''
                CREATE TABLE IF NOT EXISTS cycle_events (
                  sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                  event_id TEXT NOT NULL UNIQUE,
                  kind TEXT NOT NULL,
                  payload TEXT NOT NULL,
                  state TEXT NOT NULL,
                  created_utc TEXT NOT NULL
                );
                CREATE TRIGGER IF NOT EXISTS cycle_events_no_update
                BEFORE UPDATE ON cycle_events BEGIN SELECT RAISE(ABORT, 'append-only ledger'); END;
                CREATE TRIGGER IF NOT EXISTS cycle_events_no_delete
                BEFORE DELETE ON cycle_events BEGIN SELECT RAISE(ABORT, 'append-only ledger'); END;
            ''')

    def _connect(self):
        con = sqlite3.connect(self.path, timeout=30)
        con.execute('PRAGMA busy_timeout=30000')
        con.execute('PRAGMA synchronous=FULL')
        return con

    @staticmethod
    def _empty():
        return dict(initialized=False, protectedreserve=0, tradingcash=0, unallocatedcash=0,
                    totalcash=0, cycle_startstake=0, cycle_id=None, status='uninitialized', used_cycle_ids=[])

    @staticmethod
    def _public(state):
        result = dict(state)
        result.pop('used_cycle_ids', None)
        for key in ('protectedreserve', 'tradingcash', 'unallocatedcash', 'totalcash', 'cycle_startstake'):
            result[key] = money(result[key])
        return result

    def state(self):
        with closing(self._connect()) as con:
            row = con.execute('SELECT state FROM cycle_events ORDER BY sequence DESC LIMIT 1').fetchone()
        return self._public(json.loads(row[0]) if row else self._empty())

    def events(self):
        with closing(self._connect()) as con:
            rows = con.execute('SELECT sequence,event_id,kind,payload,state,created_utc FROM cycle_events ORDER BY sequence').fetchall()
        return [dict(sequence=r[0], event_id=r[1], kind=r[2], payload=json.loads(r[3]),
                     state=self._public(json.loads(r[4])), created_utc=r[5]) for r in rows]

    def _append(self, event_id, kind, payload, transition):
        if not isinstance(event_id, str) or not event_id.strip():
            raise LedgerError('A nonempty unique event_id is required')
        serialized = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        con = self._connect()
        try:
            con.execute('BEGIN IMMEDIATE')
            old = con.execute('SELECT kind,payload,state FROM cycle_events WHERE event_id=?', (event_id,)).fetchone()
            if old:
                if old[0] != kind or old[1] != serialized:
                    raise LedgerError('event_id already exists with a different request')
                con.commit()
                return self._public(json.loads(old[2]))
            row = con.execute('SELECT state FROM cycle_events ORDER BY sequence DESC LIMIT 1').fetchone()
            state = json.loads(row[0]) if row else self._empty()
            transition(state)
            balances = [state[k] for k in ('protectedreserve', 'tradingcash', 'unallocatedcash')]
            if any(v < 0 for v in balances):
                raise LedgerError('Cash cannot be negative; reserves cannot fund losses')
            state['totalcash'] = sum(balances)
            if state['totalcash'] > 10**15:
                raise LedgerError('Account exceeds supported ledger range')
            con.execute('INSERT INTO cycle_events(event_id,kind,payload,state,created_utc) VALUES(?,?,?,?,?)',
                        (event_id, kind, serialized, json.dumps(state, sort_keys=True), datetime.now(timezone.utc).isoformat()))
            con.commit()
            return self._public(state)
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def initialize(self, event_id, starting_capital='51.00', *, verified=False):
        amount = cents(starting_capital)
        if verified is not True:
            raise LedgerError('Starting capital must be verified')
        def apply(s):
            if s['initialized']: raise LedgerError('Account already initialized')
            s.update(initialized=True, tradingcash=amount, status='ready')
        return self._append(event_id, 'initialize', dict(starting_capital_cents=amount, verified=True), apply)

    def open_cycle(self, event_id, cycle_id):
        if not isinstance(cycle_id, str) or not cycle_id.strip():
            raise LedgerError('A unique nonempty cycle_id is required')
        def apply(s):
            if not s['initialized']: raise LedgerError('Initialize verified capital first')
            if s['status'] == 'open': raise LedgerError('A cycle is already open')
            if cycle_id in s['used_cycle_ids']: raise LedgerError('cycle_id was already used')
            if s['tradingcash'] <= 0: raise LedgerError('No trading stake remains')
            s.update(cycle_id=cycle_id, cycle_startstake=s['tradingcash'], status='open')
            s['used_cycle_ids'].append(cycle_id)
        return self._append(event_id, 'open_cycle', dict(cycle_id=cycle_id), apply)

    def external_cashflow(self, event_id, direction, amount, *, verified=False):
        value = cents(amount)
        if direction not in ('deposit', 'withdrawal') or value <= 0:
            raise LedgerError('Specify deposit or withdrawal and a positive amount')
        if verified is not True: raise LedgerError('External cashflow must be verified')
        def apply(s):
            if not s['initialized']: raise LedgerError('Initialize verified capital first')
            # External money is quarantined; never counted as strategy P&L or stake.
            if direction == 'withdrawal' and value > s['unallocatedcash']:
                raise LedgerError('Withdrawal exceeds unallocated cash; reserve and stake remain protected')
            s['unallocatedcash'] += value if direction == 'deposit' else -value
        return self._append(event_id, 'external_cashflow', dict(direction=direction, amount_cents=value, verified=True), apply)

    def close_cycle(self, event_id, cycle_id, *, terminal_equity, gross_realized_pnl,
                    fees, reconciled=False, open_positions=None, open_orders=None):
        terminal = cents(terminal_equity)
        gross = cents(gross_realized_pnl, signed=True)
        fee = cents(fees)
        if reconciled is not True:
            raise LedgerError('Closing settlement must be reconciled')
        if type(open_positions) is not int or type(open_orders) is not int or open_positions != 0 or open_orders != 0:
            raise LedgerError('A completely closed cycle requires zero positions and zero orders')
        def apply(s):
            if s['status'] != 'open' or s['cycle_id'] != cycle_id:
                raise LedgerError('Matching open cycle required')
            stake = s['cycle_startstake']
            net = gross-fee
            if terminal != stake+net:
                raise LedgerError('Reconciliation failed: terminal equity must equal start stake + gross realized P&L - fees')
            if net > 0:
                s['protectedreserve'] += stake
                s['tradingcash'] = net
            else:
                s['tradingcash'] = terminal
            s['status'] = 'closed'
        return self._append(event_id, 'close_cycle', dict(cycle_id=cycle_id, terminal_equity_cents=terminal,
                            gross_realized_pnl_cents=gross, fees_cents=fee, reconciled=True,
                            open_positions=0, open_orders=0), apply)


Ledger = CycleLedger
