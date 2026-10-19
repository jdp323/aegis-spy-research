"""AEGIS V2: persistent CAD-only paper proposal gate; never places orders.

All verification flags are input attestations supplied by a trusted reconciler.
They are not authentication, a brokerage integration, or an OS security boundary.
"""
from dataclasses import dataclass, asdict
import json
import math
import sqlite3
import time
from typing import Mapping


@dataclass(frozen=True)
class CycleLedger:
    cycle_id: str
    cycle_number: int
    starting_capital_cad: float
    trading_stake_cad: float
    protected_cash_cad: float
    loss_cap_cad: float
    cumulative_loss_cad: float
    timestamp: float
    verified: bool = False


@dataclass(frozen=True)
class AccountSnapshot:
    equity_cad: float
    peak_equity_cad: float
    own_cash_cad: float
    open_risk_cad: float
    open_positions: int
    open_order_count: int
    open_orders_reserved_cash_cad: float
    holdings: Mapping[str, int]
    sell_reserved_quantities: Mapping[str, int]
    ledger: CycleLedger
    timestamp: float
    reconciled: bool = False
    open_orders_verified: bool = False
    currency: str = "CAD"


@dataclass(frozen=True)
class MarketQuote:
    symbol: str
    bid: float
    ask: float
    timestamp: float
    currency: str = "CAD"


@dataclass(frozen=True)
class MarketSession:
    symbol: str
    is_open: bool
    timestamp: float
    verified: bool = False


@dataclass(frozen=True)
class StrategyEvidence:
    evidence_id: str
    validated_at: float
    valid_until: float
    approved: bool = False


@dataclass(frozen=True)
class Proposal:
    proposal_id: str
    symbol: str
    side: str
    quantity: int
    limit_price: float
    fees_cad: float
    fees_known: bool
    gap_inclusive_loss_cad: float
    expected_net_profit_cad: float
    counter_thesis: str
    strategy_id: str
    evidence_id: str
    expires_at: float
    currency: str = "CAD"


@dataclass(frozen=True)
class Decision:
    status: str
    reason: str
    proposal_id: str = ""
    expires_at: float = 0.0
    reserved_cash_cad: float = 0.0
    reserved_risk_cad: float = 0.0
    execution_authorized: bool = False


def _number(x):
    try:
        return type(x) in (int, float) and math.isfinite(x)
    except OverflowError:
        return False


def _fresh(stamp, now, max_age):
    return _number(stamp) and _number(now) and 0 <= now - stamp <= max_age


def _text(x):
    return isinstance(x, str) and bool(x.strip())


def _symbol(x):
    return _text(x) and x == x.strip().upper()


class RiskEngineV2:
    ACCOUNT_MAX_AGE = 60
    QUOTE_MAX_AGE = 30
    SESSION_MAX_AGE = 60
    STRATEGY_MAX_AGE = 30 * 86400
    PROPOSAL_MAX_LIFE = 300
    FLOOR_CAD = 30.0
    PEAK_DRAWDOWN_FRACTION = 0.40

    def __init__(self, database_path, strategy_registry=None):
        self.registry = dict(strategy_registry or {})
        self.db = sqlite3.connect(database_path, timeout=10, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
          PRAGMA journal_mode=WAL;
          CREATE TABLE IF NOT EXISTS v2_control (
            id INTEGER PRIMARY KEY CHECK(id=1), halt TEXT);
          INSERT OR IGNORE INTO v2_control VALUES(1,NULL);
          CREATE TABLE IF NOT EXISTS v2_peak (
            id INTEGER PRIMARY KEY CHECK(id=1), equity REAL NOT NULL);
          CREATE TABLE IF NOT EXISTS v2_proposals (
            proposal_id TEXT PRIMARY KEY, payload TEXT NOT NULL,
            symbol TEXT NOT NULL, side TEXT NOT NULL, quantity INTEGER NOT NULL,
            cash REAL NOT NULL, risk REAL NOT NULL, expires REAL NOT NULL,
            status TEXT NOT NULL, cycle_id TEXT NOT NULL);
          CREATE UNIQUE INDEX IF NOT EXISTS v2_pending_economic_duplicate
            ON v2_proposals(symbol,side) WHERE status='PENDING_RESEARCH_ONLY';
          CREATE TABLE IF NOT EXISTS v2_ledgers (
            cycle_id TEXT PRIMARY KEY, cycle_number INTEGER UNIQUE NOT NULL,
            starting REAL NOT NULL, stake REAL NOT NULL, protected REAL NOT NULL,
            loss_cap REAL NOT NULL, cumulative_loss REAL NOT NULL);
          CREATE TABLE IF NOT EXISTS v2_audit (
            id INTEGER PRIMARY KEY, created REAL NOT NULL, action TEXT NOT NULL,
            proposal_id TEXT NOT NULL, detail TEXT NOT NULL);
        """)

    def close(self):
        self.db.close()

    def _audit(self, action, proposal_id, reason):
        self.db.execute("INSERT INTO v2_audit(created,action,proposal_id,detail) VALUES(?,?,?,?)",
                        (time.time(), action, proposal_id, reason))

    def _account_error(self, a, now):
        if not isinstance(a, AccountSnapshot) or a.reconciled is not True or a.open_orders_verified is not True:
            return "Account and open orders require verified reconciliation"
        if a.currency != "CAD" or not _fresh(a.timestamp, now, self.ACCOUNT_MAX_AGE):
            return "Only fresh CAD account snapshots are supported"
        if not all(_number(x) for x in (a.equity_cad, a.peak_equity_cad, a.own_cash_cad,
                                       a.open_risk_cad, a.open_orders_reserved_cash_cad)):
            return "Invalid account numeric values"
        if (a.equity_cad < 0 or a.peak_equity_cad <= 0 or a.peak_equity_cad < a.equity_cad
                or not 0 <= a.own_cash_cad <= a.equity_cad or a.open_risk_cad < 0
                or not 0 <= a.open_orders_reserved_cash_cad <= a.own_cash_cad
                or type(a.open_positions) is not int or a.open_positions < 0
                or type(a.open_order_count) is not int or a.open_order_count < 0):
            return "Inconsistent account amounts or counts"
        remembered_peak = self.db.execute("SELECT equity FROM v2_peak WHERE id=1").fetchone()
        if remembered_peak and a.peak_equity_cad < remembered_peak[0]:
            return "Peak equity cannot be reset downward"
        if not isinstance(a.holdings, Mapping) or not isinstance(a.sell_reserved_quantities, Mapping):
            return "Verified holdings and externally reserved sales are required"
        if any(not _symbol(s) or type(n) is not int or n < 0 for s, n in a.holdings.items()):
            return "Invalid holdings"
        if a.open_positions < sum(n > 0 for n in a.holdings.values()):
            return "Position count understates verified holdings"
        if any(not _symbol(s) or type(n) is not int or not 0 <= n <= a.holdings.get(s, 0)
               for s, n in a.sell_reserved_quantities.items()):
            return "Invalid reserved sales"
        l = a.ledger
        if (not isinstance(l, CycleLedger) or l.verified is not True or not _text(l.cycle_id)
                or type(l.cycle_number) is not int or l.cycle_number < 1
                or not _fresh(l.timestamp, now, self.ACCOUNT_MAX_AGE)):
            return "Verified fresh cycle ledger required"
        if not all(_number(x) for x in (l.starting_capital_cad, l.trading_stake_cad,
                                        l.protected_cash_cad, l.loss_cap_cad, l.cumulative_loss_cad)):
            return "Invalid ledger numeric values"
        if (l.starting_capital_cad <= 0 or not 0 < l.trading_stake_cad <= l.starting_capital_cad
                or l.protected_cash_cad < 0 or l.protected_cash_cad > a.own_cash_cad
                or not 0 < l.loss_cap_cad <= l.trading_stake_cad or l.cumulative_loss_cad < 0):
            return "Inconsistent cycle stake, reserve, or loss cap"
        if l.cycle_number == 1 and (l.starting_capital_cad != 51 or l.loss_cap_cad > 21):
            return "Cycle one requires CAD51 starting capital and at most CAD21 loss cap"
        old = self.db.execute("SELECT * FROM v2_ledgers WHERE cycle_id=?", (l.cycle_id,)).fetchone()
        latest = self.db.execute("SELECT MAX(cycle_number) FROM v2_ledgers").fetchone()[0]
        if latest is not None and l.cycle_number < latest:
            return "Cannot reuse a previous cycle ledger"
        if old:
            if (l.cycle_number != old["cycle_number"] or l.starting_capital_cad != old["starting"]
                    or l.trading_stake_cad > old["stake"] or l.protected_cash_cad < old["protected"]
                    or l.loss_cap_cad > old["loss_cap"] or l.cumulative_loss_cad < old["cumulative_loss"]):
                return "Ledger cannot replenish used loss budget or unprotect funds"
        elif latest is not None:
            if l.cycle_number <= latest:
                return "Cycle identity conflicts with persisted ledger"
            if self.db.execute("SELECT 1 FROM v2_proposals WHERE status='PENDING_RESEARCH_ONLY'").fetchone():
                return "Resolve prior-cycle reservations before admitting a new cycle"
            previous = self.db.execute("SELECT protected FROM v2_ledgers ORDER BY cycle_number DESC LIMIT 1").fetchone()
            if l.protected_cash_cad < previous[0]:
                return "Prior protected reserve cannot be reused"
        return None

    def _remember_ledger(self, l):
        self.db.execute("""INSERT INTO v2_ledgers VALUES(?,?,?,?,?,?,?)
          ON CONFLICT(cycle_id) DO UPDATE SET stake=excluded.stake,
          protected=excluded.protected,loss_cap=excluded.loss_cap,cumulative_loss=excluded.cumulative_loss""",
          (l.cycle_id, l.cycle_number, l.starting_capital_cad, l.trading_stake_cad,
           l.protected_cash_cad, l.loss_cap_cad, l.cumulative_loss_cad))

    def evaluate(self, account, quote, session, proposal, *, now=None):
        now = time.time() if now is None else now
        self.db.execute("BEGIN IMMEDIATE")
        try:
            result = self._evaluate(account, quote, session, proposal, now)
            self._audit(result.status, result.proposal_id, result.reason)
            self.db.execute("COMMIT")
            return result
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def _evaluate(self, a, q, session, p, now):
        pid = p.proposal_id if isinstance(p, Proposal) and isinstance(p.proposal_id, str) else ""
        reject = lambda reason: Decision("REJECTED", reason, pid)
        error = self._account_error(a, now)
        if error:
            return reject(error)
        self._remember_ledger(a.ledger)
        self.db.execute("INSERT INTO v2_peak VALUES(1,?) ON CONFLICT(id) DO UPDATE SET equity=MAX(equity,excluded.equity)",
                        (a.peak_equity_cad,))
        breach = ("CAD30 equity floor" if a.equity_cad <= self.FLOOR_CAD else
                  "40% peak drawdown" if a.peak_equity_cad-a.equity_cad >= a.peak_equity_cad*self.PEAK_DRAWDOWN_FRACTION else
                  "Cycle loss cap exhausted" if a.ledger.cumulative_loss_cad >= a.ledger.loss_cap_cad else None)
        if breach:
            self.db.execute("UPDATE v2_control SET halt=COALESCE(halt,?) WHERE id=1", (breach,))
        halt = self.db.execute("SELECT halt FROM v2_control WHERE id=1").fetchone()[0]
        if not isinstance(p, Proposal):
            return reject("Proposal required")
        if (not all(_text(x) for x in (p.proposal_id, p.strategy_id, p.evidence_id, p.counter_thesis))
                or not _symbol(p.symbol) or p.side not in ("BUY", "SELL")
                or p.currency != "CAD" or type(p.quantity) is not int or p.quantity <= 0
                or not _number(p.quantity)):
            return reject("Invalid identity, CAD currency, side, whole-share quantity, or counter-thesis")
        # Risk-reducing exit research remains possible during an entry halt.
        if halt and p.side == "BUY":
            return reject("PERSISTENT_HALT: " + halt)
        if (not isinstance(q, MarketQuote) or q.symbol != p.symbol or q.currency != "CAD"
                or not _number(q.bid) or not _number(q.ask) or not 0 < q.bid <= q.ask
                or not _fresh(q.timestamp, now, self.QUOTE_MAX_AGE)):
            return reject("Invalid, stale, future, crossed, or non-CAD quote")
        if (not isinstance(session, MarketSession) or session.symbol != p.symbol
                or session.verified is not True or session.is_open is not True
                or not _fresh(session.timestamp, now, self.SESSION_MAX_AGE)):
            return reject("Verified fresh open market session required")
        evidence = self.registry.get(p.strategy_id)
        if (not isinstance(evidence, StrategyEvidence) or evidence.approved is not True
                or evidence.evidence_id != p.evidence_id
                or not _fresh(evidence.validated_at, now, self.STRATEGY_MAX_AGE)
                or not _number(evidence.valid_until) or evidence.valid_until <= now):
            return reject("Missing, mismatched, or stale validated strategy evidence")
        if (not all(_number(x) for x in (p.limit_price, p.fees_cad, p.gap_inclusive_loss_cad,
                                         p.expected_net_profit_cad, p.expires_at))
                or p.limit_price <= 0 or p.fees_known is not True or p.fees_cad < 0
                or p.gap_inclusive_loss_cad < 0):
            return reject("Invalid or unknown prices, fees, or modeled loss")
        payload = json.dumps(asdict(p), sort_keys=True, allow_nan=False)
        existing = self.db.execute("SELECT * FROM v2_proposals WHERE proposal_id=?", (p.proposal_id,)).fetchone()
        if existing and existing["payload"] != payload:
            return reject("Proposal ID already used for different economic terms")
        if p.expires_at <= now:
            return Decision("EXPIRED_REVIEW_REQUIRED" if existing and existing["status"] == "PENDING_RESEARCH_ONLY" else "REJECTED",
                            "Expired proposal; existing reservations require explicit reconciliation", pid, p.expires_at)
        if p.expires_at - now > self.PROPOSAL_MAX_LIFE:
            return reject("Proposal expiry exceeds five-minute maximum")
        if evidence.valid_until < p.expires_at:
            return reject("Strategy evidence expires before proposal")
        if existing and existing["status"] != "PENDING_RESEARCH_ONLY":
            return reject("Proposal ID is terminal and cannot be reused")
        duplicate = self.db.execute("SELECT proposal_id FROM v2_proposals WHERE symbol=? AND side=? AND status='PENDING_RESEARCH_ONLY'",
                                    (p.symbol, p.side)).fetchone()
        if duplicate and duplicate[0] != pid:
            return reject("Pending economic duplicate; expiry never releases a reservation")
        pending = self.db.execute("SELECT * FROM v2_proposals WHERE status='PENDING_RESEARCH_ONLY' AND proposal_id<>?", (pid,)).fetchall()
        pending_cash = sum(r["cash"] for r in pending)
        pending_risk = sum(r["risk"] for r in pending)
        cash = risk = 0.0
        if p.side == "BUY":
            if p.gap_inclusive_loss_cad <= 0 or p.expected_net_profit_cad <= 0:
                return reject("BUY requires positive gap-inclusive modeled loss and positive net expected profit")
            cash = p.quantity * p.limit_price + p.fees_cad
            risk = p.gap_inclusive_loss_cad + p.fees_cad
            if not _number(cash) or not _number(risk):
                return reject("Calculation overflow")
            if p.limit_price < q.ask:
                return reject("BUY proposal limit below current ask; refresh research assumptions")
            if a.equity_cad < 500 and a.open_positions + a.open_order_count + sum(r["side"] == "BUY" for r in pending) >= 2:
                return reject("Two-position cap includes open orders and pending BUY proposals")
            spendable = min(a.own_cash_cad-a.ledger.protected_cash_cad-a.open_orders_reserved_cash_cad,
                            a.ledger.trading_stake_cad-a.ledger.cumulative_loss_cad
                            -(a.equity_cad-a.own_cash_cad)-a.open_orders_reserved_cash_cad) - pending_cash
            if cash > spendable:
                return reject("Insufficient own unprotected cycle cash; borrowing and reserve reuse prohibited")
            available = min(a.ledger.loss_cap_cad-a.ledger.cumulative_loss_cad,
                            a.equity_cad-self.FLOOR_CAD,
                            a.peak_equity_cad*self.PEAK_DRAWDOWN_FRACTION-(a.peak_equity_cad-a.equity_cad)) - a.open_risk_cad-pending_risk
            if risk > available:
                return reject("Insufficient cycle/floor/peak modeled-risk budget")
        else:
            reserved_sales = sum(r["quantity"] for r in pending if r["side"] == "SELL" and r["symbol"] == p.symbol)
            available_shares = a.holdings.get(p.symbol, 0)-a.sell_reserved_quantities.get(p.symbol, 0)-reserved_sales
            if p.quantity > available_shares:
                return reject("SELL exceeds verified unreserved holdings; shorts prohibited")
            if p.limit_price > q.bid or p.quantity*p.limit_price < p.fees_cad:
                return reject("SELL price or net proceeds inconsistent with current quote/known fees")
        if not existing:
            self.db.execute("INSERT INTO v2_proposals VALUES(?,?,?,?,?,?,?,?,?,?)",
                            (pid, payload, p.symbol, p.side, p.quantity, cash, risk, p.expires_at,
                             "PENDING_RESEARCH_ONLY", a.ledger.cycle_id))
        elif existing["cycle_id"] != a.ledger.cycle_id:
            return reject("Proposal belongs to another cycle")
        return Decision("PENDING_RESEARCH_ONLY", "Paper proposal only; manual owner review required", pid,
                        p.expires_at, cash, risk)

    def pending(self, *, now=None):
        """Read-only records. Expired records keep reservations, but are non-actionable."""
        now = time.time() if now is None else now
        if not _number(now):
            raise ValueError("Finite epoch timestamp required")
        records = []
        for row in self.db.execute("SELECT * FROM v2_proposals WHERE status='PENDING_RESEARCH_ONLY'"):
            item = dict(row)
            item["review_status"] = "EXPIRED_REVIEW_REQUIRED" if row["expires"] <= now else "FRESH_REVIEW_REQUIRED"
            item["execution_authorized"] = False
            records.append(item)
        return records

    def resolve(self, proposal_id, *, status, owner_confirmation, reason, reconciled_account, now=None):
        """Release only after explicit owner report plus fresh account reconciliation."""
        if owner_confirmation is not True or not _text(reason) or status not in ("OWNER_CANCELLED", "OWNER_EXECUTED_RECONCILED"):
            raise ValueError("Explicit owner confirmation, reason, and supported terminal status required")
        now = time.time() if now is None else now
        self.db.execute("BEGIN IMMEDIATE")
        try:
            error = self._account_error(reconciled_account, now)
            if error:
                raise ValueError(error)
            row = self.db.execute("SELECT * FROM v2_proposals WHERE proposal_id=?", (proposal_id,)).fetchone()
            if not row:
                raise ValueError("Unknown proposal ID")
            if row["status"] != "PENDING_RESEARCH_ONLY" and row["status"] != status:
                raise ValueError("Terminal status cannot be changed")
            self._remember_ledger(reconciled_account.ledger)
            self.db.execute("INSERT INTO v2_peak VALUES(1,?) ON CONFLICT(id) DO UPDATE SET equity=MAX(equity,excluded.equity)",
                            (reconciled_account.peak_equity_cad,))
            self.db.execute("UPDATE v2_proposals SET status=? WHERE proposal_id=?", (status, proposal_id))
            self._audit(status, proposal_id, reason)
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def reset_halt(self, *, owner_confirmation, reason):
        if owner_confirmation is not True or not _text(reason):
            raise ValueError("Explicit owner confirmation and reset reason required")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self.db.execute("UPDATE v2_control SET halt=NULL WHERE id=1")
            self._audit("OWNER_HALT_RESET", "", reason)
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise
