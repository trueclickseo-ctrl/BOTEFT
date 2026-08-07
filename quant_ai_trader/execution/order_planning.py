"""Translate approved target allocations into deterministic broker order previews."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from quant_ai_trader.execution.allocation import validate_target_weights
from quant_ai_trader.execution.broker_interface import OrderRequest


@dataclass(frozen=True)
class OrderPlan:
    approved: bool
    orders: tuple[OrderRequest, ...]
    blockers: tuple[str, ...]
    residual_cash: float


def translate_target_weights(*, weights: dict[str, float], prices: dict[str, float],
                             current_quantities: dict[str, int], instruments: dict[str, dict],
                             sectors: dict[str, str], equity: float, account_key: str,
                             strategy: str, price_as_of: datetime,
                             now: datetime | None = None, max_price_age: timedelta = timedelta(minutes=15)) -> OrderPlan:
    validation = validate_target_weights(weights, sectors)
    blockers = list(validation.blockers)
    now = now or datetime.now(UTC)
    if price_as_of.tzinfo is None:
        price_as_of = price_as_of.replace(tzinfo=UTC)
    if now - price_as_of > max_price_age:
        blockers.append("market prices are stale")
    if equity <= 0: blockers.append("equity must be positive")
    symbols = sorted(set(current_quantities) | {s for s in weights if s != "CASH"})
    for symbol in symbols:
        if symbol not in prices or prices[symbol] <= 0: blockers.append(f"{symbol}: valid price required")
        if symbol not in instruments: blockers.append(f"{symbol}: Saxo instrument mapping required")
    if blockers:
        return OrderPlan(False, (), tuple(dict.fromkeys(blockers)), equity)
    orders: list[OrderRequest] = []
    target_notional = 0.0
    for symbol in symbols:
        target_shares = int((equity * weights.get(symbol, 0.0)) // prices[symbol])
        delta = target_shares - int(current_quantities.get(symbol, 0))
        target_notional += target_shares * prices[symbol]
        if not delta: continue
        side = "Buy" if delta > 0 else "Sell"
        digest = hashlib.sha256(f"{strategy}|{price_as_of.date()}|{symbol}|{side}|{abs(delta)}".encode()).hexdigest()[:20]
        details = instruments[symbol]
        orders.append(OrderRequest(symbol, int(details["uic"]), str(details.get("asset_type", "Etf")),
                                   account_key, side, abs(delta), strategy, f"botef-{digest}"))
    return OrderPlan(True, tuple(orders), (), max(equity - target_notional, 0.0))
