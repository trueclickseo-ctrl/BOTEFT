import pandas as pd
from quant_ai_trader.backtesting.defensive_momentum import DefensiveMomentumConfig, run_defensive_momentum_backtest, select_ranked_with_hysteresis


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


def test_existing_position_band_never_suppresses_entries_or_exits(sample_bars):
    frames = {symbol: sample_bars for symbol in ("SPY", "QQQ", "GLD")}
    common = dict(momentum_lookback_days=20, trend_lookback_days=20,
                  volatility_lookback_days=10, rebalance_days=10)
    _, decisions, _ = run_defensive_momentum_backtest(
        frames, DefensiveMomentumConfig(**common, existing_position_rebalance_threshold=.01))
    changed = decisions[decisions.membership_changes > 0]
    assert (changed.order_count > 0).all()


def test_risk_adjusted_ranking_remains_unlevered_and_capped(sample_bars):
    frames = {symbol: sample_bars for symbol in ("SPY", "QQQ", "GLD")}
    config = DefensiveMomentumConfig(momentum_lookback_days=20, trend_lookback_days=20,
        volatility_lookback_days=10, rebalance_days=10, risk_adjusted_momentum_ranking=True)
    _, decisions, _ = run_defensive_momentum_backtest(frames, config)
    assert decisions.exposure.max() <= config.holdings * config.maximum_etf_weight + 1e-12
    assert {"regime_exits", "momentum_exits", "ma_exits", "rank_exits"}.issubset(decisions.columns)


def test_spy_hysteresis_state_persists_inside_band(sample_bars):
    frames = {symbol: sample_bars for symbol in ("SPY", "QQQ", "GLD")}
    config = DefensiveMomentumConfig(momentum_lookback_days=20, trend_lookback_days=20,
        volatility_lookback_days=10, rebalance_days=5, spy_regime_hysteresis=.02)
    _, decisions, _ = run_defensive_momentum_backtest(frames, config)
    inside = decisions.spy_ma_distance.abs() < .02
    states = decisions.risk_on
    assert ((states[inside] == states.shift()[inside]) | states.shift()[inside].isna()).all()


def test_rank_hysteresis_retains_incumbent_at_rank_ten():
    symbols = [f"S{i}" for i in range(1, 12)]
    score = pd.Series(range(11, 0, -1), index=symbols, dtype=float)
    eligible = pd.Series(True, index=symbols)
    selected = select_ranked_with_hysteresis(score, eligible, {"S10"}, holdings=8, buffer=2)
    assert "S10" in selected
    assert "S8" not in selected


def test_continuous_spy_regime_multiplier_is_bounded(sample_bars):
    frames = {symbol: sample_bars for symbol in ("SPY", "QQQ", "GLD")}
    config = DefensiveMomentumConfig(momentum_lookback_days=20, trend_lookback_days=20,
        volatility_lookback_days=10, rebalance_days=5, continuous_spy_regime_width=.05)
    _, decisions, _ = run_defensive_momentum_backtest(frames, config)
    assert decisions.spy_regime_multiplier.between(0, 1).all()


def test_longer_cadence_produces_fewer_rebalances(sample_bars):
    frames = {symbol: sample_bars for symbol in ("SPY", "QQQ", "GLD")}
    common = dict(momentum_lookback_days=20, trend_lookback_days=20, volatility_lookback_days=10)
    short = run_defensive_momentum_backtest(frames, DefensiveMomentumConfig(**common, rebalance_days=5))[1]
    long = run_defensive_momentum_backtest(frames, DefensiveMomentumConfig(**common, rebalance_days=10))[1]
    assert len(long) < len(short)
