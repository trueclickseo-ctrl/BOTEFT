"""Bullish-regime RSI pullback strategy."""
import pandas as pd

def rsi_mean_reversion_signals(features: pd.DataFrame) -> pd.DataFrame:
    required = {"adjusted_close", "sma_200", "rsi_14", "spy_trend_50"}
    missing = required - set(features.columns)
    if missing: raise ValueError(f"Mean-reversion features missing: {sorted(missing)}")
    result = pd.DataFrame(index=features.index)
    trend_ok = (features["adjusted_close"] > features["sma_200"]) & (features["spy_trend_50"] > 0)
    result["entry_signal"] = trend_ok & (features["rsi_14"] < 35)
    result["exit_signal"] = (features["rsi_14"] > 55) | ~trend_ok
    return result
