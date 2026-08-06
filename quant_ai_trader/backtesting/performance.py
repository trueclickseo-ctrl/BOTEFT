"""Portfolio and trade-level performance metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_performance(equity_curve: pd.Series, trades: pd.DataFrame, trading_days_per_year: int = 252) -> dict[str, float]:
    """Calculate standard metrics from a marked-to-market equity curve and closed trades."""
    if equity_curve.empty:
        raise ValueError("Equity curve cannot be empty")
    equity = equity_curve.astype(float)
    total_return = equity.iloc[-1] / equity.iloc[0] - 1
    periods = max(len(equity) - 1, 1)
    annual_return = (equity.iloc[-1] / equity.iloc[0]) ** (trading_days_per_year / periods) - 1
    returns = equity.pct_change().dropna()
    volatility = returns.std(ddof=0)
    sharpe = float(np.sqrt(trading_days_per_year) * returns.mean() / volatility) if volatility > 0 else 0.0
    drawdown = equity / equity.cummax() - 1
    maximum_drawdown = float(drawdown.min())
    if trades.empty:
        return {
            "total_return": float(total_return), "annual_return": float(annual_return), "sharpe_ratio": sharpe,
            "maximum_drawdown": maximum_drawdown, "win_rate": 0.0, "profit_factor": 0.0, "number_of_trades": 0.0,
        }
    pnl = trades["net_pnl"].astype(float)
    gross_profit, gross_loss = pnl[pnl > 0].sum(), -pnl[pnl < 0].sum()
    profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)
    return {
        "total_return": float(total_return), "annual_return": float(annual_return), "sharpe_ratio": sharpe,
        "maximum_drawdown": maximum_drawdown, "win_rate": float((pnl > 0).mean()), "profit_factor": profit_factor,
        "number_of_trades": float(len(trades)),
    }
