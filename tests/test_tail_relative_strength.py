import numpy as np
import pandas as pd

from quant_ai_trader.risk.tail_relative_strength import relative_strength_filter, tail_risk_multiplier


def test_tail_overlay_does_not_reduce_initial_clean_period():
    returns = pd.Series([0.001] * 400, index=pd.date_range("2020-01-01", periods=400, freq="B"))
    assert (tail_risk_multiplier(returns) == 1).all()


def test_tail_overlay_uses_only_prior_day():
    dates = pd.date_range("2020-01-01", periods=400, freq="B")
    returns = pd.Series(np.sin(np.arange(400)) * .02, index=dates)
    first = tail_risk_multiplier(returns, vol_lookback_for_zscore=40)
    changed = returns.copy(); changed.iloc[-1] = -.5
    second = tail_risk_multiplier(changed, vol_lookback_for_zscore=40)
    assert first.iloc[-1] == second.iloc[-1]


def test_relative_strength_rebalances_after_holiday_week_close():
    dates = pd.bdate_range("2024-01-01", "2024-02-01").difference(pd.DatetimeIndex(["2024-01-05"]))
    prices = pd.DataFrame({"A": np.arange(len(dates)) + 100, "B": np.arange(len(dates)) + 90}, index=dates)
    weights = relative_strength_filter(prices, lookback=2, skip_recent=1, top_n=1)
    assert weights.loc[pd.Timestamp("2024-01-08")].sum() == 1
