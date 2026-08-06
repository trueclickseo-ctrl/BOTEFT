"""AI probability-based ETF entry and exit rules for research/backtesting."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class StrategyRules:
    buy_probability_threshold: float = 75.0
    exit_probability_threshold: float = 45.0
    target_return: float = 0.06
    stop_loss: float = 0.03
    maximum_holding_days: int = 30

    def __post_init__(self) -> None:
        if self.target_return / self.stop_loss < 2.0:
            raise ValueError("target_return / stop_loss must be at least 2.0 under the trading rules")

    @property
    def risk_reward_ratio(self) -> float:
        return self.target_return / self.stop_loss


def generate_signals(features: pd.DataFrame, rules: StrategyRules = StrategyRules()) -> pd.DataFrame:
    """Generate research signals using values known at the close of each session.

    Entries are designed to execute at the following session's open in the backtester,
    preventing same-bar execution leakage.
    """
    required = {"buy_probability", "spy_trend_50"}
    missing = required - set(features.columns)
    if missing:
        raise ValueError(f"Strategy features missing: {sorted(missing)}")
    signals = pd.DataFrame(index=features.index)
    probabilities = features["buy_probability"].astype(float)
    if probabilities.dropna().between(0, 1).all():
        probabilities = probabilities * 100
    signals["buy_probability"] = probabilities
    signals["market_bullish"] = features["spy_trend_50"].astype(float) > 0
    signals["risk_reward"] = rules.risk_reward_ratio
    signals["entry_signal"] = (
        (signals["buy_probability"] >= rules.buy_probability_threshold)
        & (signals["risk_reward"] >= 2.0)
        & signals["market_bullish"]
    )
    signals["exit_signal"] = signals["buy_probability"] < rules.exit_probability_threshold
    return signals
