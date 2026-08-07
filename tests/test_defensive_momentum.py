import pandas as pd
from quant_ai_trader.backtesting.defensive_momentum import DefensiveMomentumConfig, run_defensive_momentum_backtest


def test_defensive_momentum_is_capped_and_uses_prior_signal(sample_bars):
    dates = pd.date_range("2020-01-01", periods=280, freq="B")
    spy = sample_bars.reindex(dates).ffill().bfill()
    frames = {"SPY": spy, "QQQ": spy.assign(adjusted_close=spy.adjusted_close * 1.01),
              "GLD": spy.assign(adjusted_close=spy.adjusted_close * .99)}
    config = DefensiveMomentumConfig(momentum_lookback_days=20, trend_lookback_days=20,
                                     volatility_lookback_days=10, rebalance_days=10)
    _, decisions, _ = run_defensive_momentum_backtest(frames, config)
    assert not decisions.empty
    assert decisions["exposure"].max() <= config.holdings * config.maximum_etf_weight + 1e-12
    assert (decisions["signal_date"] < decisions["date"]).all()


def test_defensive_momentum_costs_reduce_equity(sample_bars):
    frames = {symbol: sample_bars for symbol in ("SPY", "QQQ", "GLD")}
    config = dict(momentum_lookback_days=20, trend_lookback_days=20, volatility_lookback_days=10, rebalance_days=10)
    free = run_defensive_momentum_backtest(frames, DefensiveMomentumConfig(**config, trading_cost_bps=0, fixed_cost_per_order=0))[0]
    costed = run_defensive_momentum_backtest(frames, DefensiveMomentumConfig(**config, trading_cost_bps=30, fixed_cost_per_order=1))[0]
    assert costed.iloc[-1] <= free.iloc[-1]


def test_weekly_overlay_charges_resize_turnover(sample_bars):
    frames = {symbol: sample_bars for symbol in ("SPY", "QQQ", "GLD")}
    config = DefensiveMomentumConfig(momentum_lookback_days=20, trend_lookback_days=20,
        volatility_lookback_days=10, rebalance_days=10, dynamic_vol_targeting=True,
        resize_days=5, resize_threshold=0)
    _, _, metrics = run_defensive_momentum_backtest(frames, config)
    assert metrics["total_turnover"] >= 0
    assert metrics["order_count"] >= metrics["resize_count"]
