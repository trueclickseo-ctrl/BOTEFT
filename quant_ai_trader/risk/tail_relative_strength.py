"""No-look-ahead tail-risk and cross-sectional relative-strength tools."""
from __future__ import annotations

import numpy as np
import pandas as pd


def strategy_drawdown(strategy_returns: pd.Series) -> pd.Series:
    equity = (1 + strategy_returns.fillna(0.0)).cumprod()
    return equity / equity.cummax() - 1.0


def tail_risk_multiplier(
    strategy_returns: pd.Series,
    dd_threshold: float = -.05,
    vol_window: int = 20,
    vol_zscore_threshold: float = 1.5,
    vol_lookback_for_zscore: int = 252,
    cut_exposure: float = .3,
    cooldown_days: int = 10,
) -> pd.Series:
    """Transition-only overlay; weights at t use observations through t-1."""
    dd = strategy_drawdown(strategy_returns)
    vol = strategy_returns.rolling(vol_window, min_periods=vol_window).std(ddof=1)
    mean = vol.rolling(vol_lookback_for_zscore, min_periods=vol_lookback_for_zscore).mean()
    std = vol.rolling(vol_lookback_for_zscore, min_periods=vol_lookback_for_zscore).std(ddof=1)
    triggered = ((dd < dd_threshold) & (((vol - mean) / std.replace(0, np.nan)) > vol_zscore_threshold)).fillna(False)
    reduced, clean = False, cooldown_days
    values = []
    for trigger in triggered:
        if trigger:
            reduced, clean = True, 0
        elif reduced:
            clean += 1
            if clean >= cooldown_days:
                reduced = False
        values.append(cut_exposure if reduced else 1.0)
    return pd.Series(values, index=strategy_returns.index).shift(1).fillna(1.0)


def tail_risk_overlay(strategy_returns: pd.Series, raw_signal: pd.Series, **kwargs) -> pd.Series:
    return raw_signal * tail_risk_multiplier(strategy_returns, **kwargs).reindex(raw_signal.index).ffill()


def momentum_score(prices: pd.DataFrame, lookback: int = 126, skip_recent: int = 21) -> pd.DataFrame:
    return prices.shift(skip_recent) / prices.shift(lookback + skip_recent) - 1.0


def relative_strength_filter(
    prices: pd.DataFrame,
    lookback: int = 126,
    skip_recent: int = 21,
    top_n: int = 5,
    rebalance_freq: str = "W-FRI",
) -> pd.DataFrame:
    """Weights selected at an actual period-ending session and effective next session."""
    scores = momentum_score(prices, lookback, skip_recent)
    periods = prices.index.to_period(rebalance_freq)
    actual_rebalance_dates = set(prices.groupby(periods).tail(1).index)
    weights = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    current = pd.Series(0.0, index=prices.columns)
    for date in prices.index:
        weights.loc[date] = current
        if date in actual_rebalance_dates:
            row = scores.loc[date].dropna()
            top = row[row > 0].nlargest(top_n).index
            current = pd.Series(0.0, index=prices.columns)
            if len(top):
                current.loc[top] = 1 / len(top)
    return weights
