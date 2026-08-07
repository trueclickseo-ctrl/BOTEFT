"""Publish the frozen stock strategy's latest decision and execution context."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import math
import pandas as pd

from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.operations.strategy_approval import approval_for
from quant_ai_trader.strategies.stocks.core_satellite import (
    StockCoreSatelliteConfig, build_stock_core_satellite_weights,
)
from quant_ai_trader.workflows.stocks.data import STOCK_DATABASE
from quant_ai_trader.workflows.stocks.universe import US_STOCK_UNIVERSE


STRATEGY = "stock_core_satellite_consolidated_v1"


@dataclass(frozen=True)
class StockDecision:
    action: str
    symbol: str | None
    reason: str
    signal_is_active: bool
    target_weight: float
    signal_date: str
    last_rebalance_date: str
    next_review_date: str
    price: float | None
    trailing_momentum: float | None
    current_quantity: int
    indicative_target_quantity: int | None
    strategy_status: str
    submission_authorized: bool
    blockers: tuple[str, ...]
    target_weights: dict[str, float]
    saxo_instrument: dict | None = None


def _aligned_prices(repository: MarketDataRepository) -> pd.DataFrame:
    frames = {symbol: repository.load_bars(symbol) for symbol in US_STOCK_UNIVERSE}
    missing = [symbol for symbol, frame in frames.items() if frame.empty]
    if missing:
        raise ValueError(f"Stock history missing for: {', '.join(missing)}")
    dates = sorted(set.intersection(*(set(frame.index) for frame in frames.values())))
    prices = pd.DataFrame({
        symbol: frames[symbol].loc[dates, "adjusted_close"] for symbol in US_STOCK_UNIVERSE
    }, index=dates)
    if len(prices) < 254:
        raise ValueError("At least 254 aligned sessions are required for a stock decision")
    return prices


def build_decision(*, database_path=STOCK_DATABASE,
                   current_quantities: dict[str, int] | None = None,
                   current_tactical_symbol: str | None = None,
                   account_equity: float | None = None,
                   saxo_instruments: dict[str, dict] | None = None) -> StockDecision:
    """Return a deterministic decision; never submits or prechecks an order."""
    current_quantities = {key.upper(): int(value) for key, value in (current_quantities or {}).items()}
    prices = _aligned_prices(MarketDataRepository(database_path))
    config = StockCoreSatelliteConfig()
    weights, _ = build_stock_core_satellite_weights(prices, config)
    latest = weights.iloc[-1]
    changes = weights.ne(weights.shift()).any(axis=1)
    last_rebalance = weights.index[changes][-1]
    satellite = latest[latest >= config.maximum_stock_weight - 1e-12]
    symbol = str(satellite.idxmax()) if not satellite.empty else None
    held = {key for key, quantity in current_quantities.items() if quantity > 0}
    current_tactical_symbol = current_tactical_symbol.upper() if current_tactical_symbol else None

    if symbol is None:
        action = "EXIT" if held else "CASH"
        reason = "No stock has positive 252-session momentum at the latest scheduled review."
    elif current_quantities.get(symbol, 0) > 0:
        action = "HOLD"
        reason = f"{symbol} remains the strongest positive 252-session momentum stock."
    elif current_tactical_symbol and current_tactical_symbol != symbol:
        action = "ROTATE"
        reason = f"Rotate the tactical sleeve from {current_tactical_symbol} to {symbol}."
    else:
        action = "BUY"
        reason = f"{symbol} is the strongest positive 252-session momentum stock."

    signal_index = prices.index.get_loc(last_rebalance) - 1
    momentum = None
    price = None
    if symbol:
        price = float(prices.loc[prices.index[-1], symbol])
        momentum = float(prices.iloc[signal_index][symbol] / prices.iloc[signal_index-config.momentum_lookback_days][symbol] - 1)
    quantity = None
    if symbol and account_equity is not None and account_equity > 0:
        quantity = math.floor(account_equity * float(latest[symbol]) / price)

    approval = approval_for(STRATEGY)
    blockers = []
    if not approval.may_submit_paper_order:
        blockers.append(f"strategy is {approval.status}: {approval.reason}")
    if account_equity is None or account_equity <= 0:
        blockers.append("positive Saxo account equity is required for whole-share sizing")
    instrument = (saxo_instruments or {}).get(symbol) if symbol else None
    if symbol and instrument is None:
        blockers.append(f"{symbol}: Saxo stock instrument mapping has not been attached")
    if prices.index[-1].date() < date.today():
        blockers.append(f"market data is stale: latest session is {prices.index[-1].date()}")

    next_review = (pd.Timestamp(last_rebalance) + pd.offsets.BDay(config.rebalance_days)).date()
    return StockDecision(
        action=action, symbol=symbol, reason=reason, signal_is_active=action in {"BUY", "HOLD", "ROTATE"},
        target_weight=float(latest.get(symbol, 0.0)) if symbol else 0.0,
        signal_date=str(prices.index[signal_index].date()), last_rebalance_date=str(last_rebalance.date()),
        next_review_date=str(next_review), price=price, trailing_momentum=momentum,
        current_quantity=current_quantities.get(symbol, 0) if symbol else 0,
        indicative_target_quantity=quantity, strategy_status=str(approval.status),
        submission_authorized=not blockers and approval.may_submit_paper_order,
        blockers=tuple(blockers), target_weights={key: float(value) for key, value in latest.items() if value > 0},
        saxo_instrument=instrument,
    )


def run(*, validate_saxo: bool = False, **kwargs) -> dict:
    decision = build_decision(**kwargs)
    if validate_saxo and decision.symbol:
        from quant_ai_trader.workflows.stocks.saxo_lookup import resolve
        mapping = resolve((decision.symbol,))["resolved"]
        kwargs["saxo_instruments"] = mapping
        decision = build_decision(**kwargs)
    return asdict(decision)


if __name__ == "__main__":
    print(run())
