from quant_ai_trader.backtesting.momentum_low_vol import run_backtest
from quant_ai_trader.features.feature_pipeline import build_feature_dataset
def test_momentum_low_vol_backtest_runs(sample_bars):
    frames={s:build_feature_dataset(sample_bars,sample_bars) for s in ("AAA","BBB","CCC")}
    curve,log,metrics=run_backtest(frames)
    assert not curve.empty and not log.empty and "sharpe_ratio" in metrics
