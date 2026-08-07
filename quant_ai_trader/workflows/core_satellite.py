"""Research-only core-satellite blend of passive and defensive ETF sleeves."""
from __future__ import annotations
import argparse
import pandas as pd
from quant_ai_trader.backtesting.blended_portfolio import blend_equity_curves
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
    satellite, _, _ = run_risk_targeted_dual_momentum_backtest(frames)
    core, _ = run_volatility_matched_equal_weight_backtest(frames)
    blended, metrics = blend_equity_curves(core, satellite, core_weight=.5)
    start = int(len(blended) * .60); window = (len(blended) - start) // folds
    fold_details = []
    for fold in range(folds):
        left = start + fold * window; right = start + (fold + 1) * window if fold < folds - 1 else len(blended)
        blend_metrics = calculate_performance(blended.iloc[left - 1:right], pd.DataFrame())
        core_metrics = calculate_performance(core.iloc[left - 1:right], pd.DataFrame())
        fold_details.append({"fold": fold + 1, "start": str(blended.index[left].date()), "end": str(blended.index[right - 1].date()), "blend_sharpe": blend_metrics["sharpe_ratio"], "core_sharpe": core_metrics["sharpe_ratio"], "blend_total_return": blend_metrics["total_return"], "core_total_return": core_metrics["total_return"], "blend_maximum_drawdown": blend_metrics["maximum_drawdown"]})
    metrics["core_weight"] = .5
    metrics["research_only"] = 1.0
    metrics["folds"] = float(folds)
    metrics["sharpe_wins"] = float(sum(item["blend_sharpe"] > item["core_sharpe"] for item in fold_details))
    metrics["worst_fold_drawdown"] = float(min(item["blend_maximum_drawdown"] for item in fold_details))
    metrics["validation_status"] = "candidate_for_operator_review" if metrics["worst_fold_drawdown"] >= -.20 and metrics["sharpe_wins"] >= folds - 1 else "insufficient_unseen_evidence"
    metrics["fold_details"] = fold_details
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_UNIVERSE)); parser.add_argument("--folds", type=int, default=4)
    args = parser.parse_args(); print(run(args.symbols, args.folds))
