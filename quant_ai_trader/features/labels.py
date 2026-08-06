"""Point-in-time trade-outcome labels for supervised learning."""

from __future__ import annotations

import numpy as np
import pandas as pd


def create_target_stop_labels(
    bars: pd.DataFrame,
    target_return: float = 0.06,
    stop_loss: float = 0.03,
    holding_period_days: int = 30,
) -> pd.DataFrame:
    """Label whether a target is reached before a stop within the holding window.

    Entry is the close on the signal date. A bar that crosses both levels is labelled
    as a loss because intraday ordering is unknowable from daily OHLC data; this is
    intentionally conservative. Rows without a complete future horizon have no label.
    """
    if not 0 < target_return:
        raise ValueError("target_return must be positive")
    if not 0 < stop_loss < 1:
        raise ValueError("stop_loss must be between zero and one")
    if holding_period_days < 1:
        raise ValueError("holding_period_days must be at least one")
    required = {"high", "low", "adjusted_close"}
    missing = required - set(bars.columns)
    if missing:
        raise ValueError(f"Missing label columns: {sorted(missing)}")

    result = bars.copy().sort_index()
    close = result["adjusted_close"].astype(float).to_numpy()
    highs = result["high"].astype(float).to_numpy()
    lows = result["low"].astype(float).to_numpy()
    labels = np.full(len(result), np.nan)
    exits = np.full(len(result), np.nan)
    days_to_exit = np.full(len(result), np.nan)

    for entry_index in range(0, len(result) - holding_period_days):
        entry = close[entry_index]
        if not np.isfinite(entry) or entry <= 0:
            continue
        target, stop = entry * (1 + target_return), entry * (1 - stop_loss)
        for offset in range(1, holding_period_days + 1):
            index = entry_index + offset
            hit_target, hit_stop = highs[index] >= target, lows[index] <= stop
            if hit_target or hit_stop:
                # Stop wins an ambiguous daily bar: conservative and deterministic.
                labels[entry_index] = float(hit_target and not hit_stop)
                exits[entry_index] = stop if hit_stop else target
                days_to_exit[entry_index] = offset
                break
        else:
            labels[entry_index] = 0.0
            exits[entry_index] = close[entry_index + holding_period_days]
            days_to_exit[entry_index] = holding_period_days

    result["target_hit_before_stop"] = pd.Series(labels, index=result.index, dtype="Float64")
    result["realized_return"] = exits / result["adjusted_close"] - 1
    result["days_to_exit"] = pd.Series(days_to_exit, index=result.index, dtype="Float64")
    return result
