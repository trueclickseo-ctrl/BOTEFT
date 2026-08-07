"""Canonical target-weight execution and exact-cost accounting engine."""
from __future__ import annotations

from dataclasses import dataclass
import pandas as pd

from quant_ai_trader.backtesting.performance import calculate_performance


@dataclass(frozen=True)
class WeightEngineConfig:
    initial_cash: float = 100_000.0
    commission_bps: float = 8.0
    minimum_commission: float = 1.0
    fx_and_slippage_bps: float = 30.0


def run_weight_backtest(prices: pd.DataFrame, target_weights: pd.DataFrame,
                        config: WeightEngineConfig = WeightEngineConfig(),
                        cash_returns: pd.Series | None = None):
    prices, target_weights = prices.align(target_weights, join="inner", axis=0)
    target_weights = target_weights.reindex(columns=prices.columns, fill_value=0.0).fillna(0.0)
    if (target_weights < -1e-12).any().any():
        raise ValueError("Long-only target weights cannot be negative")
    if (target_weights.sum(axis=1) > 1 + 1e-12).any():
        raise ValueError("Target weights cannot exceed available capital")
    if cash_returns is None:
        cash_returns = pd.Series(0.0, index=prices.index)
    else:
        cash_returns = cash_returns.reindex(prices.index).ffill().fillna(0.0).astype(float)
        if (cash_returns <= -1).any():
            raise ValueError("Cash return cannot be less than or equal to -100 percent")
    returns = prices.pct_change(fill_method=None).fillna(0.0)
    equity, weights, curve, costs = config.initial_cash, pd.Series(0.0, index=prices.columns), [], []
    total_turnover, order_count = 0.0, 0
    previous_target = None
    for date in prices.index:
        desired = target_weights.loc[date]
        target_changed = previous_target is None or not desired.equals(previous_target)
        traded = pd.Series(dtype=float)
        variable = commission = turnover = 0.0
        if target_changed:
            changes = (desired - weights).abs()
            traded = changes[changes > 1e-12]
            pretrade = equity
            variable = pretrade * float(traded.sum()) * config.fx_and_slippage_bps / 10_000
            commission = sum(max(pretrade * float(change) * config.commission_bps / 10_000,
                                 config.minimum_commission) for change in traded)
            equity = max(equity - variable - commission, 0.0)
            turnover = float(traded.sum())
            total_turnover += turnover
            order_count += len(traded)
            weights = desired.copy()
            previous_target = desired.copy()
        period_returns = returns.loc[date]
        cash_weight = max(1.0 - float(weights.sum()), 0.0)
        portfolio_return = float((weights * period_returns).sum()) + cash_weight * float(cash_returns.loc[date])
        equity *= max(1 + portfolio_return, 0.0)
        if 1 + portfolio_return > 0:
            weights = weights * (1 + period_returns) / (1 + portfolio_return)
        curve.append(equity)
        if target_changed and turnover:
            costs.append({"date": date, "turnover": turnover, "orders": len(traded),
                          "variable_cost": variable, "commission": commission})
    equity_curve = pd.Series(curve, index=prices.index, name="equity")
    metrics = calculate_performance(equity_curve, pd.DataFrame())
    metrics.update({"total_turnover": total_turnover,
                    "annualized_turnover": total_turnover / (len(prices) / 252),
                    "order_count": float(order_count), "rebalance_events": float(len(costs))})
    return equity_curve, pd.DataFrame(costs), metrics
