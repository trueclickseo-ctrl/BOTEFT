from quant_ai_trader.data.quality import validate_daily_bars

def test_data_quality_accepts_valid_bars_and_rejects_invalid_ohlc(sample_bars):
    assert validate_daily_bars(sample_bars).valid
    invalid = sample_bars.copy(); invalid.iloc[0, invalid.columns.get_loc("high")] = 1
    report = validate_daily_bars(invalid)
    assert not report.valid and "invalid_ohlc_range" in report.errors
