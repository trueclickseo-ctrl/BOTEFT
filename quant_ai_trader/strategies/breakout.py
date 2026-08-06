"""Medium-term breakout signals with ATR-based risk distance."""
import pandas as pd

def breakout_signals(features: pd.DataFrame) -> pd.DataFrame:
    required = {"adjusted_close", "sma_200", "atr_14", "spy_trend_50"}
    missing = required - set(features.columns)
    if missing: raise ValueError(f"Breakout features missing: {sorted(missing)}")
    close = features["adjusted_close"]
    high_55 = close.rolling(55).max().shift(1)
    low_20 = close.rolling(20).min().shift(1)
    output = pd.DataFrame(index=features.index)
    output["entry_signal"] = (close > high_55) & (close > features["sma_200"]) & (features["spy_trend_50"] > 0)
    output["exit_signal"] = (close < low_20) | (features["spy_trend_50"] <= 0)
    output["stop_loss_fraction"] = (2 * features["atr_14"] / close).clip(.01, .03)
    output["target_return_fraction"] = output["stop_loss_fraction"] * 2
    return output
