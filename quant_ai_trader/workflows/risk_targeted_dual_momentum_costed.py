"""Cost and capital sensitivity for the fixed risk-targeted rotation strategy."""
from __future__ import annotations

from quant_ai_trader.backtesting.dual_momentum import RiskTargetedDualMomentumConfig, run_risk_targeted_dual_momentum_backtest
from quant_ai_trader.config.settings import Settings
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.workflows.breakout_universe import DEFAULT_UNIVERSE


def run(capital_levels: tuple[float, ...] = (1_000.0, 10_000.0, 100_000.0)) -> dict[str, object]:
    repository = MarketDataRepository(Settings().database_path)
    frames = {symbol: repository.load_bars(symbol) for symbol in DEFAULT_UNIVERSE}
    results = []
    for capital in capital_levels:
        normal = RiskTargetedDualMomentumConfig(initial_cash=capital, trading_cost_bps=30.0, fixed_cost_per_order=1.0)
        stress = RiskTargetedDualMomentumConfig(initial_cash=capital, trading_cost_bps=60.0, fixed_cost_per_order=2.0)
        _, decisions, metrics = run_risk_targeted_dual_momentum_backtest(frames, normal)
        _, _, stress_metrics = run_risk_targeted_dual_momentum_backtest(frames, stress)
        results.append({"initial_capital": capital, "total_return": metrics["total_return"],
                        "sharpe_ratio": metrics["sharpe_ratio"], "maximum_drawdown": metrics["maximum_drawdown"],
                        "rebalance_count": len(decisions), "doubled_cost_total_return": stress_metrics["total_return"],
                        "economically_positive": metrics["total_return"] > 0 and stress_metrics["total_return"] > 0})
    return {"strategy": "risk_targeted_dual_momentum_v1", "cost_assumptions": {
        "fixed_cost_per_order": 1.0, "variable_round_trip_bps": 60.0,
        "stressed_fixed_cost_per_order": 2.0, "stressed_variable_round_trip_bps": 120.0,
    }, "capital_sensitivity": results, "paper_trading_approved": False}


if __name__ == "__main__": print(run())
