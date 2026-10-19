"""Pure first-cycle research calculator; no orders, state mutation or live approval."""
from decimal import Decimal, InvalidOperation


def amount(value):
    if value is None or isinstance(value, bool):
        raise ValueError('Missing or invalid amount')
    try:
        value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError('Invalid amount') from None
    if not value.is_finite() or value < 0:
        raise ValueError('Amounts must be finite and nonnegative')
    return value


def remaining_budget(*, equity, verified_peak, own_cash, protected_cash,
                     existing_modeled_risk, reserved_cash, external_cash_flows):
    """CAD-only first cycle, starting capital 51; inputs must be reconciled.

    Any subsequent funding/withdrawal requires a separate cash-flow reconciliation
    implementation. This calculator rejects such changes rather than calling them
    gains/losses. All modeled losses supplied must include costs and gap stress.
    The result is a ceiling, not a position recommendation or a loss guarantee.
    """
    if external_cash_flows is None or Decimal(str(external_cash_flows)) != 0:
        raise ValueError('External cash flows require reconciliation; unsupported here')
    e, peak, cash, protected, exposure, reserved = map(amount, (
        equity, verified_peak, own_cash, protected_cash, existing_modeled_risk, reserved_cash))
    if peak < max(e, Decimal('51')) or cash > e or protected > cash or reserved > cash-protected:
        raise ValueError('Inconsistent reconciled snapshot')
    if protected != 0:
        raise ValueError('Protected profits imply a later cycle; use a validated later-cycle ledger')
    # Profits do not increase the fixed first-cycle CAD21 loss allowance.
    used_loss = max(Decimal('0'), Decimal('51')-e)
    limits = {
        'cycle': Decimal('21')-used_loss-exposure,
        'floor': e-Decimal('30')-exposure,
        'drawdown': peak*Decimal('0.40')-(peak-e)-exposure,
        'cash': cash-protected-reserved,
    }
    return {'maximum_additional_modeled_loss_cad': max(Decimal('0'),min(limits.values())),
            'cash_available_cad': limits['cash'],
            'binding_constraints': [k for k,v in limits.items() if v==min(limits.values())],
            'execution_authorized': False}
