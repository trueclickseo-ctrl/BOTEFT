"""Fixed-rule, rolling unseen validation for risk-targeted dual momentum."""
from __future__ import annotations
import argparse
import pandas as pd
from quant_ai_trader.backtesting.dual_momentum import run_risk_targeted_dual_momentum_backtest, run_volatility_matched_equal_weight_backtest
from quant_ai_trader.backtesting.performance import calculate_performance
from quant_ai_trader.config.settings import Settings
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.workflows.breakout_universe import DEFAULT_UNIVERSE


def run(symbols: list[str], folds: int = 4) -> dict[str, object]:
    if folds < 2: raise ValueError("At least two validation folds are required")
    repo = MarketDataRepository(Settings().database_path)
    frames = {symbol.upper(): repo.load_bars(symbol.upper()) for symbol in symbols}
    missing = [symbol for symbol, frame in frames.items() if frame.empty]
    if missing: raise ValueError(f"Missing stored bars for: {', '.join(missing)}")
    curve, _, _ = run_risk_targeted_dual_momentum_backtest(frames)
    benchmark_curve, _ = run_volatility_matched_equal_weight_backtest(frames)
    start = int(len(curve) * .60); window = (len(curve) - start) // folds
    strategy_folds, benchmark_folds, fold_details = [], [], []
    for fold in range(folds):
        left = start + fold * window; right = start + (fold + 1) * window if fold < folds - 1 else len(curve)
        strategy_metrics = calculate_performance(curve.iloc[left - 1:right], pd.DataFrame())
        benchmark_metrics = calculate_performance(benchmark_curve.iloc[left - 1:right], pd.DataFrame())
        strategy_folds.append(strategy_metrics); benchmark_folds.append(benchmark_metrics)
        fold_details.append({
            "fold": fold + 1, "start": str(curve.index[left].date()), "end": str(curve.index[right - 1].date()),
            "strategy_total_return": strategy_metrics["total_return"], "strategy_sharpe": strategy_metrics["sharpe_ratio"],
            "strategy_maximum_drawdown": strategy_metrics["maximum_drawdown"],
            "benchmark_total_return": benchmark_metrics["total_return"], "benchmark_sharpe": benchmark_metrics["sharpe_ratio"],
            "benchmark_maximum_drawdown": benchmark_metrics["maximum_drawdown"],
        })
    strategy_sharpes = pd.Series([item["sharpe_ratio"] for item in strategy_folds])
    benchmark_sharpes = pd.Series([item["sharpe_ratio"] for item in benchmark_folds])
    worst_drawdown = min(item["maximum_drawdown"] for item in strategy_folds)
    return {
        "folds": float(folds),
        "average_sharpe": float(strategy_sharpes.mean()),
        "benchmark_average_sharpe": float(benchmark_sharpes.mean()),
        "average_total_return": float(pd.Series([item["total_return"] for item in strategy_folds]).mean()),
        "benchmark_average_total_return": float(pd.Series([item["total_return"] for item in benchmark_folds]).mean()),
        "worst_drawdown": float(worst_drawdown),
        "risk_gate_passed": float(worst_drawdown >= -.20),
        "sharpe_wins": float((strategy_sharpes > benchmark_sharpes).sum()),
        "validation_status": "candidate_for_operator_review" if worst_drawdown >= -.20 and (strategy_sharpes > benchmark_sharpes).sum() >= folds - 1 else "insufficient_unseen_evidence",
        "fold_details": fold_details,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_UNIVERSE)); parser.add_argument("--folds", type=int, default=4)
    print(run(parser.parse_args().symbols, parser.parse_args().folds))
