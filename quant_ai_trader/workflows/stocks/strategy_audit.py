"""Run fixed strategy families on stocks, then canonically validate candidates."""
import pandas as pd

from quant_ai_trader.backtesting.evaluation import PortfolioProfitabilityGate
from quant_ai_trader.backtesting.weight_engine import WeightEngineConfig, run_weight_backtest
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.strategies.stocks.core_satellite import build_stock_core_satellite_weights
from quant_ai_trader.workflows.stocks.data import STOCK_DATABASE
from quant_ai_trader.workflows.stocks.universe import BENCHMARK_SYMBOL, US_STOCK_UNIVERSE
from quant_ai_trader.workflows.us_strategy_cost_audit import _positive_folds, run as run_cost_audit


def _canonical_core_satellite(database_path):
    repository = MarketDataRepository(database_path)
    frames = {symbol: repository.load_bars(symbol) for symbol in US_STOCK_UNIVERSE}
    dates = sorted(set.intersection(*(set(frame.index) for frame in frames.values())))
    prices = pd.DataFrame({
        symbol: frames[symbol].loc[dates, "adjusted_close"] for symbol in US_STOCK_UNIVERSE
    }, index=dates)
    weights, unconstrained = build_stock_core_satellite_weights(prices)
    normal_curve, costs, metrics = run_weight_backtest(prices, weights, WeightEngineConfig())
    _, _, stress = run_weight_backtest(
        prices, weights,
        WeightEngineConfig(commission_bps=16, minimum_commission=2, fx_and_slippage_bps=60),
    )
    positive_folds = _positive_folds(normal_curve)
    passed, blockers = PortfolioProfitabilityGate().evaluate(
        metrics, positive_folds=positive_folds, stress_total_return=stress["total_return"]
    )
    return {
        "strategy": "stock_core_satellite_consolidated_v1",
        "total_return": metrics["total_return"],
        "sharpe_ratio": metrics["sharpe_ratio"],
        "maximum_drawdown": metrics["maximum_drawdown"],
        "positive_folds": positive_folds,
        "stress_total_return": stress["total_return"],
        "numerical_gate_pass": passed,
        "gate_blockers": list(blockers),
        "maximum_stock_weight": float(weights.max().max()),
        "average_invested_weight": float(weights.sum(axis=1).mean()),
        "cap_binding_sessions": int((unconstrained.max(axis=1) > .10 + 1e-12).sum()),
        "order_count": metrics["order_count"],
        "annualized_turnover": metrics["annualized_turnover"],
        "cost_events": len(costs),
        "paper_approved": False,
    }


def run(database_path=STOCK_DATABASE):
    result = run_cost_audit(
        database_path=database_path,
        universe=US_STOCK_UNIVERSE,
        benchmark_symbol=BENCHMARK_SYMBOL,
    )
    result["preliminary_passes"] = result["passed"]
    result["passed"] = []
    result["approved"] = 0
    result["canonical_candidate"] = _canonical_core_satellite(database_path)
    result.update({
        "asset_class": "US stocks",
        "universe": US_STOCK_UNIVERSE,
        "universe_bias": "Current-constituent survivorship bias; candidate discovery only",
        "data_limitations": [
            "Yahoo adjusted history is an unofficial personal-use research source",
            "Adjusted close reflects gross distributions; investor-specific dividend withholding tax is not modeled",
            "Saxo instrument tradability and share-level order rounding are not yet verified",
        ],
        "paper_approved": False,
        "screening_note": "ETF-specific diversified result is inapplicable; independent-curve core-satellite result requires canonical validation",
    })
    return result


if __name__ == "__main__":
    print(run())
