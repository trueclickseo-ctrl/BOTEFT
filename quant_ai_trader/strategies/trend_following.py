"""Long-only trend-following ETF strategy for independent benchmark research."""
import pandas as pd

def trend_following_signals(features: pd.DataFrame) -> pd.DataFrame:
    required = {"adjusted_close", "sma_50", "sma_200", "momentum_60", "spy_trend_50"}
    missing = required - set(features.columns)
    if missing: raise ValueError(f"Trend features missing: {sorted(missing)}")
    output = pd.DataFrame(index=features.index)
    output["entry_signal"] = (features["adjusted_close"] > features["sma_50"]) & (features["sma_50"] > features["sma_200"]) & (features["momentum_60"] > 0) & (features["spy_trend_50"] > 0)
    output["exit_signal"] = (features["adjusted_close"] < features["sma_50"]) | (features["spy_trend_50"] <= 0)
    return output
