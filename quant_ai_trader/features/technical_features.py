"""Leakage-safe technical indicators computed exclusively from current/past bars."""

from __future__ import annotations

import numpy as np
import pandas as pd


def add_technical_features(bars: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of OHLCV bars enriched with standard technical features."""
    _validate_ohlcv(bars)
    frame = bars.copy().sort_index()
    close, high, low, volume = (frame[column].astype(float) for column in ("adjusted_close", "high", "low", "volume"))
    for window in (20, 50, 200):
        frame[f"sma_{window}"] = close.rolling(window, min_periods=window).mean()
    frame["ema_20"] = close.ewm(span=20, adjust=False, min_periods=20).mean()
    frame["rsi_14"] = _rsi(close, 14)
    fast = close.ewm(span=12, adjust=False, min_periods=12).mean()
    slow = close.ewm(span=26, adjust=False, min_periods=26).mean()
    frame["macd"] = fast - slow
    frame["macd_signal"] = frame["macd"].ewm(span=9, adjust=False, min_periods=9).mean()
    frame["macd_histogram"] = frame["macd"] - frame["macd_signal"]
    frame["atr_14"] = _atr(high, low, close, 14)
    middle = close.rolling(20, min_periods=20).mean()
    deviation = close.rolling(20, min_periods=20).std(ddof=0)
    frame["bollinger_upper"] = middle + 2 * deviation
    frame["bollinger_lower"] = middle - 2 * deviation
    frame["bollinger_position"] = (close - frame["bollinger_lower"]) / (frame["bollinger_upper"] - frame["bollinger_lower"])
    frame["momentum_20"] = close.pct_change(20)
    frame["volatility_20"] = close.pct_change().rolling(20, min_periods=20).std(ddof=0) * np.sqrt(252)
    frame["volume_change_5"] = volume.pct_change(5)
    frame["return_1d"] = close.pct_change()
    return frame.replace([np.inf, -np.inf], np.nan)


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gains = delta.clip(lower=0).ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    losses = (-delta.clip(upper=0)).ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    return 100 - (100 / (1 + gains / losses))


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int) -> pd.Series:
    previous_close = close.shift(1)
    true_range = pd.concat([high - low, (high - previous_close).abs(), (low - previous_close).abs()], axis=1).max(axis=1)
    return true_range.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()


def _validate_ohlcv(bars: pd.DataFrame) -> None:
    required = {"high", "low", "adjusted_close", "volume"}
    missing = required - set(bars.columns)
    if missing:
        raise ValueError(f"Missing OHLCV columns: {sorted(missing)}")
    if not isinstance(bars.index, pd.DatetimeIndex):
        raise ValueError("Bars must use a DatetimeIndex")

