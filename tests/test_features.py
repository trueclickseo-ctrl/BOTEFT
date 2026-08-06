import numpy as np

from quant_ai_trader.features.feature_pipeline import build_feature_dataset, clean_feature_dataset, model_feature_columns
from quant_ai_trader.features.technical_features import add_technical_features


def test_technical_indicators_are_created(sample_bars):
    result = add_technical_features(sample_bars)
    assert {"sma_20", "sma_200", "rsi_14", "macd", "atr_14", "volatility_20"}.issubset(result.columns)
    assert result["sma_200"].notna().sum() > 0


def test_feature_pipeline_adds_market_context(sample_bars):
    result = build_feature_dataset(sample_bars, spy_bars=sample_bars, vix_bars=sample_bars.assign(adjusted_close=20.0))
    assert {"spy_trend_50", "spy_return_20", "vix_level"}.issubset(result.columns)
    assert "sma_20" in model_feature_columns(result)


def test_cleaning_does_not_backfill_initial_missing_values(sample_bars):
    sample_bars.loc[sample_bars.index[0], "adjusted_close"] = np.nan
    cleaned = clean_feature_dataset(sample_bars)
    # Invalid price rows are discarded rather than populated with a future price.
    assert sample_bars.index[0] not in cleaned.index
