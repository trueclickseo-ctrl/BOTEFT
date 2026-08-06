"""Dataset-quality pipeline combining technical and market-context features."""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant_ai_trader.features.technical_features import add_technical_features


def build_feature_dataset(symbol_bars: pd.DataFrame, spy_bars: pd.DataFrame | None = None, vix_bars: pd.DataFrame | None = None) -> pd.DataFrame:
    """Build an ML-ready feature frame without imputation from future observations."""
    frame = add_technical_features(symbol_bars)
    if spy_bars is not None:
        spy = add_technical_features(spy_bars)
        frame["spy_trend_50"] = (spy["adjusted_close"] / spy["sma_50"] - 1).reindex(frame.index)
        frame["spy_return_20"] = spy["momentum_20"].reindex(frame.index)
    if vix_bars is not None:
        frame["vix_level"] = vix_bars["adjusted_close"].astype(float).reindex(frame.index)
    return clean_feature_dataset(frame)


def clean_feature_dataset(frame: pd.DataFrame, zscore_threshold: float = 8.0) -> pd.DataFrame:
    """Deduplicate, remove invalid prices, clip extreme numeric values, and forward-fill only."""
    cleaned = frame.copy().sort_index()
    cleaned = cleaned[~cleaned.index.duplicated(keep="last")]
    if "adjusted_close" in cleaned:
        cleaned = cleaned[cleaned["adjusted_close"] > 0]
    numeric = cleaned.select_dtypes(include=[np.number]).columns
    for column in numeric:
        series = cleaned[column]
        # Both location and dispersion are shifted by one row: future samples never
        # influence the decision to mask the current observation.
        median = series.rolling(60, min_periods=20).median().shift(1)
        mad = (series - median).abs().rolling(60, min_periods=20).median().shift(1)
        robust_z = 0.6745 * (series - median) / mad.replace(0, np.nan)
        cleaned[column] = series.mask(robust_z.abs() > zscore_threshold)
    # Forward-fill uses historical values only; never back-fill initial observations.
    return cleaned.ffill().replace([np.inf, -np.inf], np.nan)


def model_feature_columns(frame: pd.DataFrame) -> list[str]:
    """Select numerical engineered features, excluding raw prices and unobserved labels."""
    excluded = {
        "open", "high", "low", "close", "volume", "adjusted_close", "target",
        "target_hit_before_stop", "realized_return", "days_to_exit",
    }
    return [column for column in frame.select_dtypes(include=[np.number]).columns if column not in excluded]
