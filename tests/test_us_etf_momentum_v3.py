import numpy as np
import pandas as pd

from quant_ai_trader.backtesting.weight_engine import WeightEngineConfig, run_weight_backtest
from quant_ai_trader.strategies.us_etf_momentum_v3 import MomentumV3Config, base_weights, build_strategy_weights


def test_v3_keeps_unfilled_slots_in_cash():
    dates = pd.bdate_range("2020-01-01", periods=60)
    prices = pd.DataFrame({"A": np.arange(60)+100, "B": 100-np.arange(60)*.1}, index=dates)
    weights = base_weights(prices, MomentumV3Config(lookback_days=10, skip_recent_days=2, top_n=4))
    assert weights.sum(axis=1).max() <= .25


def test_v3_overlay_does_not_change_base_weights():
    dates = pd.bdate_range("2020-01-01", periods=60)
    prices = pd.DataFrame({"A": np.arange(60)+100}, index=dates)
    config = MomentumV3Config(lookback_days=10, skip_recent_days=2, top_n=1)
    base = base_weights(prices, config)
    combined = build_strategy_weights(prices, pd.Series(.3, index=dates), config)
    assert base.iloc[-1, 0] == 1
    assert combined.iloc[-1, 0] == .3


def test_weight_engine_charges_exact_minimum_commission():
    dates = pd.bdate_range("2024-01-01", periods=2)
    prices = pd.DataFrame({"A": [100., 100.]}, index=dates)
    weights = pd.DataFrame({"A": [0., .001]}, index=dates)
    _, costs, _ = run_weight_backtest(prices, weights, WeightEngineConfig(fx_and_slippage_bps=0))
    assert costs.iloc[-1]["commission"] == 1


def test_weight_engine_allows_weights_to_drift_without_rebalancing():
    dates = pd.bdate_range("2024-01-01", periods=3)
    prices = pd.DataFrame({"A": [100., 110., 121.], "B": [100., 100., 100.]}, index=dates)
    weights = pd.DataFrame({"A": [.5, .5, .5], "B": [.5, .5, .5]}, index=dates)
    _, costs, metrics = run_weight_backtest(prices, weights, WeightEngineConfig(
        commission_bps=0, minimum_commission=0, fx_and_slippage_bps=0))
    assert len(costs) == 1
    assert metrics["total_return"] > .10


def test_weight_engine_accrues_supplied_cash_return_only_on_idle_cash():
    dates = pd.bdate_range("2024-01-01", periods=3)
    prices = pd.DataFrame({"A": [100., 100., 100.]}, index=dates)
    weights = pd.DataFrame({"A": [.50, .50, .50]}, index=dates)
    cash_returns = pd.Series([0., .01, .01], index=dates)
    curve, _, _ = run_weight_backtest(
        prices, weights,
        WeightEngineConfig(commission_bps=0, minimum_commission=0, fx_and_slippage_bps=0),
        cash_returns=cash_returns,
    )
    assert curve.iloc[-1] > 101_000
    assert curve.iloc[-1] < 102_010


def test_weight_engine_defaults_to_zero_cash_yield():
    dates = pd.bdate_range("2024-01-01", periods=2)
    prices = pd.DataFrame({"A": [100., 100.]}, index=dates)
    weights = pd.DataFrame({"A": [0., 0.]}, index=dates)
    curve, _, _ = run_weight_backtest(
        prices, weights,
        WeightEngineConfig(commission_bps=0, minimum_commission=0, fx_and_slippage_bps=0),
    )
    assert curve.iloc[-1] == 100_000
