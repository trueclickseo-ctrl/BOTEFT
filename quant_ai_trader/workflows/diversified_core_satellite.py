"""Research workflow for the hard-cap diversified core-satellite strategy."""
from __future__ import annotations
import argparse
import pandas as pd
from quant_ai_trader.backtesting.diversified_core_satellite import run_diversified_core_satellite_backtest
from quant_ai_trader.backtesting.dual_momentum import run_volatility_matched_equal_weight_backtest
from quant_ai_trader.backtesting.performance import calculate_performance
from quant_ai_trader.config.settings import Settings
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.workflows.breakout_universe import DEFAULT_UNIVERSE

def run(symbols: list[str], folds: int = 4) -> dict[str, object]:
    repo = MarketDataRepository(Settings().database_path); frames = {s.upper():repo.load_bars(s.upper()) for s in symbols}
    if any(frame.empty for frame in frames.values()): raise ValueError("Missing stored bars")
    curve, rebalances, metrics = run_diversified_core_satellite_backtest(frames)
    core, _ = run_volatility_matched_equal_weight_backtest(frames)
    start, window = int(len(curve)*.60), (len(curve)-int(len(curve)*.60))//folds
    details=[]
    for fold in range(folds):
        left=start+fold*window; right=start+(fold+1)*window if fold < folds-1 else len(curve)
        a=calculate_performance(curve.iloc[left-1:right],pd.DataFrame()); b=calculate_performance(core.iloc[left-1:right],pd.DataFrame())
        details.append({"fold":fold+1,"strategy_sharpe":a["sharpe_ratio"],"core_sharpe":b["sharpe_ratio"],"strategy_drawdown":a["maximum_drawdown"],"strategy_return":a["total_return"],"core_return":b["total_return"]})
    metrics |= {"rebalances":float(len(rebalances)),"sharpe_wins":float(sum(x["strategy_sharpe"]>x["core_sharpe"] for x in details)),"worst_fold_drawdown":float(min(x["strategy_drawdown"] for x in details)),"fold_details":details,"research_only":1.0}
    metrics["validation_status"]="candidate_for_operator_review" if metrics["sharpe_wins"]>=folds-1 and metrics["worst_fold_drawdown"]>=-.20 else "insufficient_unseen_evidence"
    return metrics

if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--symbols",nargs="+",default=list(DEFAULT_UNIVERSE)); parser.add_argument("--folds",type=int,default=4); args=parser.parse_args(); print(run(args.symbols,args.folds))
