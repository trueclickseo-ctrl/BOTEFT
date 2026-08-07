"""Evaluate the single predeclared U.S. defensive-momentum redesign."""
from quant_ai_trader.backtesting.defensive_momentum import DefensiveMomentumConfig, run_defensive_momentum_backtest
from quant_ai_trader.backtesting.evaluation import PortfolioProfitabilityGate
from quant_ai_trader.config.settings import Settings
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.workflows.breakout_universe import DEFAULT_UNIVERSE
from quant_ai_trader.workflows.us_strategy_cost_audit import _positive_folds


def run() -> dict[str, object]:
    repository = MarketDataRepository(Settings().database_path)
    bars = {symbol: repository.load_bars(symbol) for symbol in DEFAULT_UNIVERSE}
    # v2 broad was declared after v1's concentrated top-three design failed:
    # widen to eight holdings and use the 150-day trend filter. Treat this as
    # research evidence, not independent confirmation, because the same history
    # informed the redesign.
    base = DefensiveMomentumConfig(holdings=8, target_annual_volatility=.10, trend_lookback_days=150)
    stress = DefensiveMomentumConfig(holdings=8, target_annual_volatility=.10, trend_lookback_days=150,
                                     trading_cost_bps=60, commission_bps=16, fixed_cost_per_order=2)
    curve, decisions, metrics = run_defensive_momentum_backtest(bars, base)
    _, _, stress_metrics = run_defensive_momentum_backtest(bars, stress)
    positive_folds = _positive_folds(curve)
    approved, blockers = PortfolioProfitabilityGate().evaluate(
        metrics, positive_folds=positive_folds, stress_total_return=stress_metrics["total_return"]
    )
    return {"strategy": "defensive_momentum_v2_broad", "rules": base.__dict__, "metrics": metrics,
            "positive_folds": positive_folds, "stress_total_return": stress_metrics["total_return"],
            "approved": approved, "blockers": list(blockers),
            "latest_decision": decisions.tail(1).to_dict("records")}


if __name__ == "__main__": print(run())
