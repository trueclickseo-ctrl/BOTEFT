from quant_ai_trader.data.quality import validate_daily_bars
from quant_ai_trader.data.database import MarketDataRepository
import pytest

def test_data_quality_accepts_valid_bars_and_rejects_invalid_ohlc(sample_bars):
    assert validate_daily_bars(sample_bars).valid
    invalid = sample_bars.copy(); invalid.iloc[0, invalid.columns.get_loc("high")] = 1
    report = validate_daily_bars(invalid)
    assert not report.valid and "invalid_ohlc_range" in report.errors


def test_repository_rejects_invalid_ohlc_before_persistence(tmp_path, sample_bars):
    invalid = sample_bars.copy()
    invalid.iloc[0, invalid.columns.get_loc("low")] = invalid.iloc[0]["high"] + 1
    repository = MarketDataRepository(tmp_path / "market.sqlite3")
    repository.initialize()
    with pytest.raises(ValueError, match="invalid_ohlc_range"):
        repository.upsert_bars("QQQ", invalid)
    assert repository.load_bars("QQQ").empty
