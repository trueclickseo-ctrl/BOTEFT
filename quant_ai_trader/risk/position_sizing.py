"""Risk-based quantity calculations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PositionSize:
    shares: int
    risk_dollars: float
    notional: float
    stop_price: float
    target_price: float


def calculate_position_size(
    account_equity: float,
    entry_price: float,
    stop_loss: float,
    target_return: float,
    risk_per_trade: float = 0.01,
    maximum_allocation: float = 0.10,
) -> PositionSize:
    """Return a whole-share position constrained by risk and allocation limits."""
    if account_equity <= 0 or entry_price <= 0:
        raise ValueError("account_equity and entry_price must be positive")
    if not 0 < stop_loss < 1 or target_return <= 0:
        raise ValueError("stop_loss must be in (0, 1) and target_return must be positive")
    stop_price = entry_price * (1 - stop_loss)
    risk_per_share = entry_price - stop_price
    risk_budget, allocation_budget = account_equity * risk_per_trade, account_equity * maximum_allocation
    shares = int(min(risk_budget / risk_per_share, allocation_budget / entry_price))
    return PositionSize(
        shares=max(shares, 0), risk_dollars=max(shares, 0) * risk_per_share,
        notional=max(shares, 0) * entry_price, stop_price=stop_price,
        target_price=entry_price * (1 + target_return),
    )
