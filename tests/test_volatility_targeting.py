import numpy as np
import pandas as pd

from quant_ai_trader.risk.volatility_targeting import combined_position_size, regime_filter, vol_target_weight


def test_vol_target_uses_only_prior_returns():
    dates = pd.date_range("2024-01-01", periods=30, freq="B")
    returns = pd.Series([.01] * 29 + [.50], index=dates)
    signal = pd.Series(1.0, index=dates)
    weights = vol_target_weight(returns, signal, window=20)
    changed = returns.copy(); changed.iloc[-1] = -.50
    changed_weights = vol_target_weight(changed, signal, window=20)
    assert weights.iloc[-1] == changed_weights.iloc[-1]


def test_regime_uses_prior_close():
    dates = pd.date_range("2024-01-01", periods=10, freq="B")
    prices = pd.Series(np.arange(10.0, 20.0), index=dates)
    first = regime_filter(prices, ma_window=3)
    changed = prices.copy(); changed.iloc[-1] = 1.0
    second = regime_filter(changed, ma_window=3)
    assert first.iloc[-1] == second.iloc[-1]


def test_combined_weight_is_leverage_capped():
    dates = pd.date_range("2024-01-01", periods=250, freq="B")
    returns = pd.Series(.0001, index=dates)
    signal = pd.Series(1.0, index=dates)
    benchmark = pd.Series(np.arange(100.0, 350.0), index=dates)
    weight = combined_position_size(returns, signal, benchmark, max_leverage=1.5)
    assert weight.dropna().abs().max() <= 1.5
