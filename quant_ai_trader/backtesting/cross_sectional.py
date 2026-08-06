"""Portfolio-level backtest for cross-sectional ETF rankings."""
from __future__ import annotations
from dataclasses import dataclass
import pandas as pd
from quant_ai_trader.backtesting.performance import calculate_performance

@dataclass(frozen=True)
class CrossSectionalConfig:
    initial_cash: float = 100_000.0
    top_n: int = 2
    rebalance_days: int = 20
    trading_cost_bps: float = 5.0
    daily_risk_off: bool = True

def run_cross_sectional_backtest(feature_frames: dict[str, pd.DataFrame], config: CrossSectionalConfig = CrossSectionalConfig()):
    """Rebalance into top-ranked ETFs after each signal close, charging turnover costs."""
    symbols = sorted(feature_frames)
    dates = sorted(set.intersection(*(set(frame.index) for frame in feature_frames.values())))
    if len(dates) < config.rebalance_days + 2: raise ValueError("Insufficient common history")
    equity, weights, curve, rebalance_log = config.initial_cash, {}, [], []
    for i, date in enumerate(dates):
        if i:
            previous = dates[i - 1]
            if config.daily_risk_off and feature_frames[symbols[0]].loc[previous, "spy_trend_50"] <= 0:
                turnover = sum(weights.values())
                equity *= 1 - turnover * config.trading_cost_bps / 10_000
                if weights: rebalance_log.append({"date": date, "symbols": "CASH", "turnover": turnover})
                weights = {}
            gross_return = sum(weights.get(symbol, 0.0) * (feature_frames[symbol].loc[date, "adjusted_close"] / feature_frames[symbol].loc[previous, "adjusted_close"] - 1) for symbol in symbols)
            equity *= 1 + gross_return
        if i > 0 and i % config.rebalance_days == 0:
            candidates = []
            for symbol, frame in feature_frames.items():
                row = frame.loc[dates[i - 1]]
                if pd.notna(row.get("momentum_60")) and row.get("spy_trend_50", 0) > 0:
                    score = (row["momentum_60"] - 3 * row.get("spy_return_20", 0)) - .25 * row.get("volatility_20", 0)
                    candidates.append((score, symbol))
            selected = [symbol for _, symbol in sorted(candidates, reverse=True)[:config.top_n]]
            target = {symbol: 1 / len(selected) for symbol in selected} if selected else {}
            turnover = sum(abs(target.get(s, 0) - weights.get(s, 0)) for s in set(target) | set(weights))
            equity *= 1 - turnover * config.trading_cost_bps / 10_000
            weights = target; rebalance_log.append({"date": date, "symbols": ",".join(selected), "turnover": turnover})
        curve.append(equity)
    equity_curve = pd.Series(curve, index=dates, name="equity")
    return equity_curve, pd.DataFrame(rebalance_log), calculate_performance(equity_curve, pd.DataFrame())
