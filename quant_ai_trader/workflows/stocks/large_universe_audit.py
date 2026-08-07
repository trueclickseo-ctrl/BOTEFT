"""Independent exact-cost tests on Nasdaq-100 and S&P 500 Top 50 universes."""
import pandas as pd
from quant_ai_trader.backtesting.evaluation import PortfolioProfitabilityGate
from quant_ai_trader.backtesting.weight_engine import WeightEngineConfig, run_weight_backtest
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.strategies.stocks.literature_momentum import build_literature_momentum_weights
from quant_ai_trader.workflows.stocks.large_universe_data import DATABASE
from quant_ai_trader.workflows.stocks.large_universes import NASDAQ_100, SP_500_TOP_50
from quant_ai_trader.workflows.us_strategy_cost_audit import _positive_folds

def _run(universe,repo):
    benchmark=repo.load_bars("SPY")["adjusted_close"]
    prices=pd.DataFrame({s:repo.load_bars(s)["adjusted_close"].reindex(benchmark.index) for s in universe})
    weights=build_literature_momentum_weights(prices,benchmark)
    normal=WeightEngineConfig(); stress_cfg=WeightEngineConfig(commission_bps=16,minimum_commission=2,fx_and_slippage_bps=60)
    curve,costs,metrics=run_weight_backtest(prices,weights,normal)
    _,_,stress=run_weight_backtest(prices,weights,stress_cfg)
    folds=_positive_folds(curve); passed,blockers=PortfolioProfitabilityGate().evaluate(metrics,positive_folds=folds,stress_total_return=stress["total_return"])
    return {"symbols":len(universe),"total_return":metrics["total_return"],"sharpe_ratio":metrics["sharpe_ratio"],
            "maximum_drawdown":metrics["maximum_drawdown"],"positive_folds":folds,"stress_total_return":stress["total_return"],
            "numerical_gate_pass":passed,"blockers":list(blockers),"annualized_turnover":metrics["annualized_turnover"],
            "orders":metrics["order_count"],"cost_events":len(costs),"paper_approved":False}

def run(database_path=DATABASE):
    repo=MarketDataRepository(database_path)
    return {"strategy":"stock_literature_momentum_v1","nasdaq_100":_run(NASDAQ_100,repo),
            "sp_500_top_50":_run(SP_500_TOP_50,repo),"bias":"current constituents projected backward"}

if __name__=="__main__": print(run())
