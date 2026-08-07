from quant_ai_trader.backtesting.diversified_core_satellite import run_diversified_core_satellite_backtest

def test_diversified_core_satellite_respects_hard_caps(sample_bars):
    frames={"SPY":sample_bars,"QQQ":sample_bars,"IWM":sample_bars,"DIA":sample_bars,"XLK":sample_bars,"XLF":sample_bars,"XLE":sample_bars,"XLV":sample_bars,"XLI":sample_bars,"XLY":sample_bars,"XLP":sample_bars,"TLT":sample_bars,"GLD":sample_bars,"SLV":sample_bars}
    curve, log, metrics=run_diversified_core_satellite_backtest(frames)
    assert not curve.empty and (log["invested"] <= 1).all() and (log["maximum_etf_weight"] <= .10).all() and (log["maximum_sector_weight"] <= .30).all() and "sharpe_ratio" in metrics
