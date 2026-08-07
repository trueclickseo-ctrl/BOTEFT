"""Predeclared cash-scaling and v2/core-satellite blend experiment."""
from __future__ import annotations

import pandas as pd

from quant_ai_trader.backtesting.defensive_momentum import DefensiveMomentumConfig, run_defensive_momentum_backtest
from quant_ai_trader.backtesting.dual_momentum import (
    RiskTargetedDualMomentumConfig,
    run_risk_targeted_dual_momentum_backtest,
    run_volatility_matched_equal_weight_backtest,
)
from quant_ai_trader.backtesting.evaluation import PortfolioProfitabilityGate
from quant_ai_trader.backtesting.performance import calculate_performance
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.workflows.breakout_universe import DEFAULT_UNIVERSE
from quant_ai_trader.workflows.us_strategy_cost_audit import _positive_folds


def _core_satellite(bars, exposure: float, stress: float) -> pd.Series:
    sleeve_capital = 100_000 * exposure / 2
    config = RiskTargetedDualMomentumConfig(
        initial_cash=sleeve_capital,
        target_annual_volatility=.10,
        trading_cost_bps=30 * stress,
        fixed_cost_per_order=1 * stress,
    )
    core, _ = run_volatility_matched_equal_weight_backtest(bars, config)
    satellite, _, _ = run_risk_targeted_dual_momentum_backtest(bars, config)
    invested = pd.concat([core, satellite], axis=1, join="inner").sum(axis=1)
    return invested + 100_000 * (1 - exposure)


def _v2(bars, capital: float, stress: float) -> pd.Series:
    config = DefensiveMomentumConfig(
        initial_cash=capital,
        holdings=8,
        target_annual_volatility=.10,
        trend_lookback_days=150,
        risk_adjusted_momentum_ranking=True,
        trading_cost_bps=30 * stress,
        fixed_cost_per_order=1 * stress,
    )
    return run_defensive_momentum_backtest(bars, config)[0]


def _result(name: str, curve: pd.Series, stress_curve: pd.Series) -> dict:
    metrics = calculate_performance(curve, pd.DataFrame())
    stress = calculate_performance(stress_curve, pd.DataFrame())
    positive_folds = _positive_folds(curve)
    approved, blockers = PortfolioProfitabilityGate().evaluate(
        metrics, positive_folds=positive_folds, stress_total_return=stress["total_return"]
    )
    return {
        "strategy": name,
        "total_return": metrics["total_return"],
        "sharpe_ratio": metrics["sharpe_ratio"],
        "maximum_drawdown": metrics["maximum_drawdown"],
        "positive_folds": positive_folds,
        "stress_total_return": stress["total_return"],
        "numerical_gate_pass": approved,
        "blockers": list(blockers),
    }


def run(database_path="data/adjusted_total_return.sqlite3") -> list[dict]:
    repository = MarketDataRepository(database_path)
    bars = {symbol: repository.load_bars(symbol) for symbol in DEFAULT_UNIVERSE}
    results = []
    for exposure in (.80, .85, .90, 1.0):
        results.append(_result(
            f"core_satellite_cash_{exposure:.2f}",
            _core_satellite(bars, exposure, 1),
            _core_satellite(bars, exposure, 2),
        ))
    for core_weight in (.25, .50, .75):
        v2_weight = 1 - core_weight
        core = _core_satellite(bars, core_weight, 1) - 100_000 * v2_weight
        stress_core = _core_satellite(bars, core_weight, 2) - 100_000 * v2_weight
        results.append(_result(
            f"core_{core_weight:.2f}_v2_{v2_weight:.2f}",
            core + _v2(bars, 100_000 * v2_weight, 1),
            stress_core + _v2(bars, 100_000 * v2_weight, 2),
        ))
    return results


if __name__ == "__main__":
    for item in run():
        print(item)
