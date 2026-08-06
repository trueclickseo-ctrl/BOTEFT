"""Cross-sectional ETF ranking for regime-aware momentum research."""
from __future__ import annotations
import pandas as pd

def rank_etfs(feature_frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Rank ETFs by 60-day momentum, SPY-relative strength, and lower volatility.

    A positive SPY trend is required; rankings are research candidates, not orders.
    """
    rows = []
    for symbol, frame in feature_frames.items():
        latest = frame.dropna(subset=["momentum_60", "volatility_20", "spy_return_20", "spy_trend_50"]).tail(1)
        if latest.empty: continue
        row = latest.iloc[0]
        if row["spy_trend_50"] <= 0: continue
        relative_strength = row["momentum_60"] - row["spy_return_20"] * 3
        score = relative_strength - 0.25 * row["volatility_20"]
        rows.append({"symbol": symbol, "score": score, "momentum_60": row["momentum_60"], "relative_strength": relative_strength, "volatility_20": row["volatility_20"]})
    return pd.DataFrame(rows).sort_values("score", ascending=False, ignore_index=True) if rows else pd.DataFrame(columns=["symbol", "score", "momentum_60", "relative_strength", "volatility_20"])
