"""US ETF momentum v3: pure signal weights, independent of risk and costs."""
from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


@dataclass(frozen=True)
class MomentumV3Config:
    lookback_days: int = 252
    skip_recent_days: int = 21
    top_n: int = 4
    minimum_score: float = 0.0
    rebalance_frequency: str = "W-FRI"


def base_weights(prices: pd.DataFrame, config: MomentumV3Config = MomentumV3Config()) -> pd.DataFrame:
    """Create next-session weights; unfilled slots remain cash."""
    if prices.empty:
        raise ValueError("prices cannot be empty")
    scores = prices.shift(config.skip_recent_days) / prices.shift(
        config.lookback_days + config.skip_recent_days
    ) - 1
    period = prices.index.to_period(config.rebalance_frequency)
    rebalance_dates = set(prices.groupby(period).tail(1).index)
    output = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    current = pd.Series(0.0, index=prices.columns)
    for date in prices.index:
        output.loc[date] = current
        if date in rebalance_dates:
            eligible = scores.loc[date].dropna()
            selected = eligible[eligible > config.minimum_score].nlargest(config.top_n).index
            current = pd.Series(0.0, index=prices.columns)
            current.loc[selected] = 1 / config.top_n
    return output


def build_strategy_weights(prices: pd.DataFrame, tail_multiplier: pd.Series,
                           config: MomentumV3Config = MomentumV3Config()) -> pd.DataFrame:
    base = base_weights(prices, config)
    multiplier = tail_multiplier.reindex(base.index).ffill().fillna(1.0)
    return base.mul(multiplier, axis=0)
