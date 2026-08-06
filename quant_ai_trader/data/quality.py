"""Pre-research integrity checks for daily OHLCV market data."""
from dataclasses import dataclass
import pandas as pd

@dataclass(frozen=True)
class DataQualityReport:
    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

def validate_daily_bars(bars: pd.DataFrame, max_gap_days: int = 7) -> DataQualityReport:
    required = {"open", "high", "low", "close", "volume", "adjusted_close"}
    missing = required - set(bars.columns)
    errors = [f"missing_columns:{','.join(sorted(missing))}"] if missing else []
    warnings: list[str] = []
    if errors or bars.empty: return DataQualityReport(False, tuple(errors or ["empty_bars"]), tuple(warnings))
    if not isinstance(bars.index, pd.DatetimeIndex) or not bars.index.is_monotonic_increasing or bars.index.has_duplicates: errors.append("invalid_timestamp_index")
    numeric = bars.loc[:, sorted(required)].astype(float)
    if (numeric[["open", "high", "low", "close", "adjusted_close"]] <= 0).any().any(): errors.append("non_positive_price")
    if (numeric["volume"] < 0).any(): errors.append("negative_volume")
    if (numeric["high"] < numeric[["open", "close"]].max(axis=1)).any() or (numeric["low"] > numeric[["open", "close"]].min(axis=1)).any(): errors.append("invalid_ohlc_range")
    if isinstance(bars.index, pd.DatetimeIndex) and len(bars) > 1 and bars.index.to_series().diff().dt.days.max() > max_gap_days: warnings.append("large_calendar_gap")
    if (numeric["adjusted_close"] == numeric["close"]).all(): warnings.append("adjusted_close_matches_raw_close")
    return DataQualityReport(not errors, tuple(errors), tuple(warnings))
