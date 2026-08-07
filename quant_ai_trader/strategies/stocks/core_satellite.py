"""Pure consolidated weights for the frozen stock core-satellite candidate."""
from __future__ import annotations

from dataclasses import dataclass
import math
import pandas as pd


@dataclass(frozen=True)
class StockCoreSatelliteConfig:
    core_allocation: float = .50
    momentum_allocation: float = .50
    maximum_stock_weight: float = .10
    momentum_lookback_days: int = 252
    volatility_lookback_days: int = 20
    rebalance_days: int = 21
    target_annual_volatility: float = .10

    def __post_init__(self):
        if not math.isclose(self.core_allocation + self.momentum_allocation, 1.0):
            raise ValueError("Stock sleeve allocations must sum to one")


def build_stock_core_satellite_weights(
    prices: pd.DataFrame,
    config: StockCoreSatelliteConfig = StockCoreSatelliteConfig(),
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if prices.empty or prices.isna().any().any() or (prices <= 0).any().any():
        raise ValueError("Stock prices must be aligned, positive, and complete")
    prices = prices.astype(float)
    returns = prices.pct_change(fill_method=None)
    core = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    momentum = core.copy()
    current_core = pd.Series(0.0, index=prices.columns)
    current_momentum = current_core.copy()
    basket_returns = returns.mean(axis=1)
    for i, date in enumerate(prices.index):
        core.loc[date] = current_core
        momentum.loc[date] = current_momentum
        vol_lookback = config.volatility_lookback_days
        if i > vol_lookback and (i - vol_lookback - 1) % config.rebalance_days == 0:
            volatility = float(basket_returns.iloc[i-vol_lookback:i].std(ddof=1) * math.sqrt(252))
            exposure = min(1.0, config.target_annual_volatility / volatility) if volatility > 0 else 0.0
            current_core = pd.Series(
                config.core_allocation * exposure / len(prices.columns), index=prices.columns
            )
        lookback = config.momentum_lookback_days
        if i > lookback and (i - lookback - 1) % config.rebalance_days == 0:
            signal = i - 1
            scores = prices.iloc[signal] / prices.iloc[signal-lookback] - 1
            selected = scores.idxmax() if scores.max() > 0 else None
            current_momentum = pd.Series(0.0, index=prices.columns)
            if selected is not None:
                volatility = float(
                    returns[selected].iloc[signal-vol_lookback+1:signal+1].std(ddof=1)
                    * math.sqrt(252)
                )
                exposure = min(1.0, config.target_annual_volatility / volatility) if volatility > 0 else 0.0
                current_momentum.loc[selected] = config.momentum_allocation * exposure
    unconstrained = core + momentum
    consolidated = unconstrained.clip(lower=0.0, upper=config.maximum_stock_weight)
    if (consolidated.sum(axis=1) > 1 + 1e-12).any():
        raise ValueError("Consolidated stock weights exceed available capital")
    return consolidated, unconstrained
