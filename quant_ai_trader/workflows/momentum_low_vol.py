"""Research workflow for a fixed monthly momentum plus low-volatility blend."""
from __future__ import annotations
import argparse
from quant_ai_trader.backtesting.dual_momentum import run_equal_weight_backtest
from quant_ai_trader.backtesting.momentum_low_vol import run_backtest
from quant_ai_trader.config.settings import Settings
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.features.feature_pipeline import build_feature_dataset
from quant_ai_trader.workflows.breakout_universe import DEFAULT_UNIVERSE

def run(symbols:list[str])->dict[str,object]:
    repo=MarketDataRepository(Settings().database_path); spy=repo.load_bars("SPY")
    frames={s.upper():build_feature_dataset(repo.load_bars(s.upper()),spy_bars=spy) for s in symbols}
    curve,_,metrics=run_backtest(frames); _,benchmark=run_equal_weight_backtest({s:repo.load_bars(s) for s in frames})
    return metrics|{"equal_weight_total_return":benchmark["total_return"],"equal_weight_sharpe":benchmark["sharpe_ratio"],"equal_weight_maximum_drawdown":benchmark["maximum_drawdown"],"research_only":True}
if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--symbols",nargs="+",default=list(DEFAULT_UNIVERSE));args=parser.parse_args();print(run(args.symbols))
