"""Execution-safe volatility targeting and benchmark regime overlays."""
from __future__ import annotations

import numpy as np
import pandas as pd


def realized_vol(returns: pd.Series, window: int = 20, annualize: bool = True) -> pd.Series:
    vol = returns.rolling(window, min_periods=window).std(ddof=1)
    return vol * np.sqrt(252) if annualize else vol


def vol_target_weight(
    returns: pd.Series,
    raw_signal: pd.Series,
    target_vol: float = .10,
    window: int = 20,
    vol_floor: float = .05,
    max_leverage: float = 1.5,
) -> pd.Series:
    """Scale using volatility known before the weight's execution session."""
    known_vol = realized_vol(returns, window).shift(1).clip(lower=vol_floor)
    scale = (target_vol / known_vol).clip(upper=max_leverage)
    return raw_signal * scale


def regime_filter(
    benchmark_prices: pd.Series,
    ma_window: int = 200,
    risk_off_multiplier: float = 0.0,
) -> pd.Series:
    """Return a regime multiplier based only on information through t-1."""
    known_price = benchmark_prices.shift(1)
    known_ma = benchmark_prices.rolling(ma_window, min_periods=ma_window).mean().shift(1)
    risk_on = known_price > known_ma
    return pd.Series(np.where(risk_on, 1.0, risk_off_multiplier), index=benchmark_prices.index)


def combined_position_size(
    symbol_returns: pd.Series,
    raw_signal: pd.Series,
    benchmark_prices: pd.Series,
    target_vol: float = .10,
    vol_window: int = 20,
    ma_window: int = 200,
    risk_off_multiplier: float = .3,
    max_leverage: float = 1.5,
) -> pd.Series:
    sized = vol_target_weight(symbol_returns, raw_signal, target_vol, vol_window,
                              max_leverage=max_leverage)
    regime = regime_filter(benchmark_prices, ma_window, risk_off_multiplier).reindex(sized.index).ffill()
    return sized * regime
