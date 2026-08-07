"""Latest allocation plan for the fixed core-satellite research candidate."""
from __future__ import annotations
import pandas as pd
from quant_ai_trader.backtesting.dual_momentum import latest_volatility_matched_exposure, run_risk_targeted_dual_momentum_backtest


def latest_target_weights(price_frames: dict[str, pd.DataFrame], core_weight: float = .5) -> dict[str, float]:
    """Return unrounded weights and cash for the static 50/50 candidate design."""
    if core_weight != .5:
        raise ValueError("Only the validated fixed 50/50 blend is supported")
    symbols = sorted(price_frames)
    _, decisions, _ = run_risk_targeted_dual_momentum_backtest(price_frames)
    latest = decisions.iloc[-1]
    core_exposure = latest_volatility_matched_exposure(price_frames)
    weights = {symbol: core_weight * core_exposure / len(symbols) for symbol in symbols}
    satellite_weight = (1 - core_weight) * float(latest["exposure"])
    if latest["holding"] != "CASH":
        symbol = str(latest["holding"])
        weights[symbol] = weights.get(symbol, 0.0) + satellite_weight
    weights["CASH"] = 1 - sum(weights.values())
    return weights
