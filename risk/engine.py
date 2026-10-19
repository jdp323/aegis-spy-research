"""Fail-closed, cash-funded, long-only PAPER research admission with reservations."""
from dataclasses import dataclass
import hashlib
import json
import math
import sqlite3
import time
from .rules import RULES


@dataclass(frozen=True)
class Account:
    equity_cad: float
    cash_cad: float
    session_start_equity_cad: float
    peak_equity_cad: float
    open_risk_cad: float
    open_positions: int
    timestamp: float
    reconciled: bool = False
    currency: str = "CAD"


@dataclass(frozen=True)
class Quote:
    symbol: str
    currency: str
    bid: float
    ask: float
    timestamp: float


@dataclass(frozen=True)
class FX:
    source_currency: str
    cad_per_unit: float
    timestamp: float
    independently_validated: bool = False


@dataclass(frozen=True)
class Proposal:
    proposal_id: str
    symbol: str
    currency: str
    quantity: int
    limit_price: float
    stop_price: float
    costs_cad: float
    modeled_loss_cad: float
    gap_stress_per_unit: float
    strategy_validation_id: str
    side: str = "BUY"


@dataclass(frozen=True)
class Decision:
    status: str
    reason: str
    reserved_risk_cad: float = 0.0
    reserved_cash_cad: float = 0.0
    execution_authorized: bool = False


def finite(*values):
    return all(isinstance(x, (int, float)) and not isinstance(x, bool)
               and math.isfinite(x) for x in values)


def fresh(stamp, now, age):
    return finite(stamp, now) and 0 <= now - stamp <= age


class RiskEngine:
    """One persistent DB per account. Inputs are trusted attestations, not fetched data.

    Never uses network, brokerage APIs, credentials, or execution adapters.
    A reservation is hypothetical and does not constitute an order.
    """
    def __init__(self, database_path, validated_strategy_ids=()):
        self.db = sqlite3.connect(database_path, isolation_level=None, timeout=10)
        self.validated_strategy_ids = frozenset(validated_strategy_ids)
        self.db.executescript("""
          PRAGMA journal_mode=WAL;
          CREATE TABLE IF NOT EXISTS control (
            singleton INTEGER PRIMARY KEY CHECK(singleton=1), halt TEXT);
          INSERT OR IGNORE INTO control VALUES(1, NULL);
          CREATE TABLE IF NOT EXISTS reservations (
            proposal_id TEXT PRIMARY KEY, economic_key TEXT UNIQUE NOT NULL,
            risk REAL NOT NULL, cash REAL NOT NULL, created REAL NOT NULL);
          CREATE TABLE IF NOT EXISTS audit (
            id INTEGER PRIMARY KEY, created REAL NOT NULL, action TEXT NOT NULL,
            detail TEXT NOT NULL);
        """)

    def close(self):
        self.db.close()

    def observe_equity_floor(self, equity_cad, *, observed_at, now=None):
        """Latch a directly verified floor breach even if session history is unknown.

        This does not reconcile an account or authorize any proposal.
        """
        now = time.time() if now is None else now
        if not finite(equity_cad) or equity_cad < 0 or not fresh(
                observed_at, now, RULES.account_max_age_seconds):
            raise ValueError("Fresh verified nonnegative equity is required")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            if equity_cad <= RULES.equity_floor_cad:
                self.db.execute("UPDATE control SET halt=COALESCE(halt,?) WHERE singleton=1",
                                ("CAD90 equity floor",))
                self.db.execute("INSERT INTO audit(created,action,detail) VALUES(?,?,?)",
                                (now, "OBSERVED_FLOOR_HALT", str(equity_cad)))
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def reset_halt(self, *, owner_confirmation, reason):
        """Explicit local owner action; not authentication. Never scheduled automatically."""
        if owner_confirmation is not True or not isinstance(reason, str) or not reason.strip():
            raise ValueError("Explicit owner confirmation and reason required")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self.db.execute("UPDATE control SET halt=NULL WHERE singleton=1")
            self.db.execute("INSERT INTO audit(created,action,detail) VALUES(?,?,?)",
                            (time.time(), "OWNER_RESET", reason))
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def evaluate(self, account, quote, fx, proposal, *, now=None):
        now = time.time() if now is None else now
        self.db.execute("BEGIN IMMEDIATE")
        try:
            result = self._evaluate(account, quote, fx, proposal, now)
            self.db.execute("INSERT INTO audit(created,action,detail) VALUES(?,?,?)",
                            (time.time(), result.status, result.reason))
            self.db.execute("COMMIT")
            return result
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def _evaluate(self, a, q, fx, p, now):
        reject = lambda reason: Decision("REJECTED", reason)
        halt = self.db.execute("SELECT halt FROM control WHERE singleton=1").fetchone()[0]
        if halt:
            return reject("PERSISTENT_HALT: " + halt)
        if not isinstance(a, Account) or a.reconciled is not True or a.currency != "CAD":
            return reject("Unknown or unreconciled CAD account")
        if not fresh(a.timestamp, now, RULES.account_max_age_seconds):
            return reject("Stale, future, or invalid account timestamp")
        if not finite(a.equity_cad, a.cash_cad, a.session_start_equity_cad,
                      a.peak_equity_cad, a.open_risk_cad):
            return reject("Invalid account numbers")
        if (a.equity_cad <= 0 or a.session_start_equity_cad <= 0
                or a.peak_equity_cad < max(a.equity_cad, a.session_start_equity_cad)
                or not 0 <= a.cash_cad <= a.equity_cad or a.open_risk_cad < 0
                or type(a.open_positions) is not int or a.open_positions < 0):
            return reject("Inconsistent account snapshot")
        daily_loss = max(0.0, a.session_start_equity_cad - a.equity_cad)
        drawdown = a.peak_equity_cad - a.equity_cad
        breach = ("CAD90 equity floor" if a.equity_cad <= RULES.equity_floor_cad else
                  "Daily loss limit" if daily_loss >= a.session_start_equity_cad * RULES.daily_loss_fraction else
                  "Peak drawdown limit" if drawdown >= a.peak_equity_cad * RULES.peak_drawdown_fraction else None)
        if breach:
            self.db.execute("UPDATE control SET halt=? WHERE singleton=1", (breach,))
            return reject("PERSISTENT_HALT: " + breach)
        if not isinstance(q, Quote) or not finite(q.bid, q.ask) or not 0 < q.bid <= q.ask:
            return reject("Nonpositive, nonfinite, or crossed quote")
        if not fresh(q.timestamp, now, RULES.quote_max_age_seconds):
            return reject("Stale, future, or invalid quote timestamp")
        if (not isinstance(fx, FX) or fx.independently_validated is not True
                or not finite(fx.cad_per_unit) or fx.cad_per_unit <= 0
                or not fresh(fx.timestamp, now, RULES.fx_max_age_seconds)):
            return reject("Missing or invalid independent FX validation")
        if not isinstance(p, Proposal):
            return reject("Missing proposal")
        if (not all(isinstance(x, str) and x.strip() for x in
                    (p.proposal_id, p.symbol, p.currency, p.strategy_validation_id))
                or p.symbol != p.symbol.strip().upper() or p.currency != p.currency.strip().upper()
                or p.side != "BUY" or type(p.quantity) is not int or p.quantity <= 0):
            return reject("Invalid identity or non-long whole-share proposal")
        if (p.symbol != q.symbol or p.currency != q.currency or p.currency != fx.source_currency
                or (p.currency == "CAD" and fx.cad_per_unit != 1)):
            return reject("Symbol or currency/FX mismatch")
        if p.strategy_validation_id not in self.validated_strategy_ids:
            return reject("Unvalidated strategy")
        if (not finite(p.limit_price, p.stop_price, p.costs_cad, p.modeled_loss_cad, p.gap_stress_per_unit)
                or not 0 < p.stop_price < p.limit_price or p.limit_price < q.ask
                or p.costs_cad < 0 or p.modeled_loss_cad <= 0 or p.gap_stress_per_unit <= 0):
            return reject("Missing or invalid costs, modeled loss, gap stress, or price")
        cash = p.quantity * p.limit_price * fx.cad_per_unit + p.costs_cad
        risk = max(p.modeled_loss_cad, p.quantity *
                   (p.limit_price - p.stop_price + p.gap_stress_per_unit) * fx.cad_per_unit) + p.costs_cad
        if not finite(cash, risk):
            return reject("Overflow in cash/risk computation")
        # Conservative duplicate definition: same instrument and side, even changed size/price.
        key = hashlib.sha256(json.dumps([p.symbol, p.currency, p.side]).encode()).hexdigest()
        if self.db.execute("SELECT 1 FROM reservations WHERE proposal_id=? OR economic_key=?",
                           (p.proposal_id, key)).fetchone():
            return reject("Duplicate proposal ID or pending economic exposure")
        count, pending_risk, pending_cash = self.db.execute(
            "SELECT COUNT(*),COALESCE(SUM(risk),0),COALESCE(SUM(cash),0) FROM reservations").fetchone()
        if a.equity_cad < RULES.small_account_threshold_cad and a.open_positions + count >= RULES.small_account_positions:
            return reject("Two-position cap includes pending reservations")
        if cash + pending_cash > a.cash_cad:
            return reject("Insufficient cash; borrowing prohibited")
        if risk > a.equity_cad * RULES.per_trade_fraction:
            return reject("Per-trade modeled risk exceeds 15% equity")
        available = min(a.session_start_equity_cad * RULES.daily_loss_fraction - daily_loss,
                        a.peak_equity_cad * RULES.peak_drawdown_fraction - drawdown,
                        a.equity_cad - RULES.equity_floor_cad) - a.open_risk_cad - pending_risk
        if risk > available:
            return reject("Insufficient remaining daily/drawdown/floor risk budget")
        self.db.execute("INSERT INTO reservations VALUES(?,?,?,?,?)",
                        (p.proposal_id, key, risk, cash, now))
        return Decision("PAPER_RESEARCH_ONLY", "Hypothetical exposure reserved; no execution authorization", risk, cash)
