"""Versioned research constraints. Separate module, NOT an OS security boundary."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Rules:
    version: str = "aegis-paper-v1"
    per_trade_fraction: float = 0.15
    daily_loss_fraction: float = 0.10
    peak_drawdown_fraction: float = 0.40
    equity_floor_cad: float = 90.0
    small_account_threshold_cad: float = 500.0
    small_account_positions: int = 2
    account_max_age_seconds: float = 60.0
    quote_max_age_seconds: float = 30.0
    fx_max_age_seconds: float = 60.0


RULES = Rules()
