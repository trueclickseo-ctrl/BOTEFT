"""Static blends of independently costed portfolio equity curves."""
from __future__ import annotations
import pandas as pd
from quant_ai_trader.backtesting.performance import calculate_performance


def blend_equity_curves(core_curve: pd.Series, satellite_curve: pd.Series, core_weight: float = .5) -> tuple[pd.Series, dict[str, float]]:
    """Allocate once to two sleeves; no hidden daily rebalancing or leverage."""
    if not 0 <= core_weight <= 1: raise ValueError("core_weight must be between zero and one")
    aligned = pd.concat([core_curve.rename("core"), satellite_curve.rename("satellite")], axis=1, join="inner")
    if aligned.empty: raise ValueError("Equity curves have no common dates")
    initial = 100_000.0
    equity = initial * (core_weight * aligned["core"] / aligned["core"].iloc[0] + (1 - core_weight) * aligned["satellite"] / aligned["satellite"].iloc[0])
    equity.name = "equity"
    return equity, calculate_performance(equity, pd.DataFrame())
