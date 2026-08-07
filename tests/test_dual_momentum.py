import numpy as np
import pandas as pd
from quant_ai_trader.backtesting.dual_momentum import DualMomentumConfig, run_dual_momentum_backtest, run_equal_weight_backtest


def test_dual_momentum_uses_prior_prices():
    dates = pd.bdate_range("2023-01-02", periods=30)
    rising = pd.Series(100 * 1.01 ** np.arange(len(dates)), index=dates)
    falling = pd.Series(100 * .99 ** np.arange(len(dates)), index=dates)
    frames = {"UP": pd.DataFrame({"adjusted_close": rising}, index=dates), "DOWN": pd.DataFrame({"adjusted_close": falling}, index=dates)}
    curve, decisions, metrics = run_dual_momentum_backtest(frames, DualMomentumConfig(lookback_days=5, rebalance_days=5))
    assert len(curve) == len(dates) and decisions.iloc[0]["holding"] == "UP" and metrics["rebalance_count"] > 0
    benchmark_curve, benchmark = run_equal_weight_backtest(frames)
    assert len(benchmark_curve) == len(dates) and "sharpe_ratio" in benchmark


def test_fixed_order_cost_reduces_small_account_result():
    dates = pd.bdate_range("2023-01-02", periods=30)
    rising = pd.Series(100 * 1.01 ** np.arange(len(dates)), index=dates)
    falling = pd.Series(100 * .99 ** np.arange(len(dates)), index=dates)
    frames = {"UP": pd.DataFrame({"adjusted_close": rising}, index=dates), "DOWN": pd.DataFrame({"adjusted_close": falling}, index=dates)}
    free = run_dual_momentum_backtest(frames, DualMomentumConfig(initial_cash=1_000, lookback_days=5, rebalance_days=5))[0]
    costed = run_dual_momentum_backtest(frames, DualMomentumConfig(initial_cash=1_000, lookback_days=5, rebalance_days=5, fixed_cost_per_order=15))[0]
    assert costed.iloc[-1] < free.iloc[-1]
