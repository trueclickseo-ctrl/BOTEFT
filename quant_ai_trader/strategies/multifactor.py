"""Multi-factor trend-quality strategy with fixed, interpretable rules."""
import pandas as pd

def multifactor_trend_signals(features: pd.DataFrame) -> pd.DataFrame:
    required = {"adjusted_close", "sma_50", "sma_200", "momentum_60", "macd_histogram", "rsi_14", "atr_14", "spy_trend_50"}
    missing = required - set(features.columns)
    if missing: raise ValueError(f"Multi-factor features missing: {sorted(missing)}")
    close = features["adjusted_close"]
    regime = features["spy_trend_50"] > 0
    trend = (close > features["sma_200"]) & (features["sma_50"] > features["sma_200"])
    quality = (features["momentum_60"] > 0) & (features["macd_histogram"] > 0) & features["rsi_14"].between(45, 70)
    output = pd.DataFrame(index=features.index)
    output["entry_signal"] = regime & trend & quality
    output["exit_signal"] = (~regime) | (close < features["sma_50"]) | (features["macd_histogram"] < 0)
    output["stop_loss_fraction"] = (2 * features["atr_14"] / close).clip(.01, .03)
    output["target_return_fraction"] = output["stop_loss_fraction"] * 2
    return output
