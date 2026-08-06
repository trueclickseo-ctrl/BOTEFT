"""Transparent benchmark strategies used to judge whether ML adds value."""
from __future__ import annotations
import pandas as pd
from quant_ai_trader.strategies.etf_strategy import StrategyRules

def momentum_baseline_signals(features: pd.DataFrame, rules: StrategyRules = StrategyRules()) -> pd.DataFrame:
    """Long-only benchmark: positive 20-day momentum in a bullish SPY regime."""
    required = {"momentum_20", "spy_trend_50"}
    missing = required - set(features.columns)
    if missing: raise ValueError(f"Baseline features missing: {sorted(missing)}")
    output = pd.DataFrame(index=features.index)
    output["entry_signal"] = (features["momentum_20"] > 0) & (features["spy_trend_50"] > 0)
    output["exit_signal"] = (features["momentum_20"] <= 0) | (features["spy_trend_50"] <= 0)
    return output
