"""Exact-cost audit of the preregistered literature momentum strategy."""
import pandas as pd
from quant_ai_trader.backtesting.evaluation import PortfolioProfitabilityGate
from quant_ai_trader.backtesting.weight_engine import WeightEngineConfig, run_weight_backtest
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.strategies.stocks.literature_momentum import build_literature_momentum_weights
from quant_ai_trader.workflows.stocks.data import STOCK_DATABASE
from quant_ai_trader.workflows.stocks.universe import BENCHMARK_SYMBOL, US_STOCK_UNIVERSE
from quant_ai_trader.workflows.us_strategy_cost_audit import _positive_folds


def run(database_path=STOCK_DATABASE):
    repo=MarketDataRepository(database_path)
    frames={s:repo.load_bars(s) for s in (*US_STOCK_UNIVERSE, BENCHMARK_SYMBOL)}
    dates=sorted(set.intersection(*(set(f.index) for f in frames.values())))
    prices=pd.DataFrame({s:frames[s].loc[dates,"adjusted_close"] for s in US_STOCK_UNIVERSE},index=dates)
    benchmark=frames[BENCHMARK_SYMBOL].loc[dates,"adjusted_close"]
    weights=build_literature_momentum_weights(prices,benchmark)
    curve,costs,metrics=run_weight_backtest(prices,weights,WeightEngineConfig())
    _,_,stress=run_weight_backtest(prices,weights,WeightEngineConfig(commission_bps=16,minimum_commission=2,fx_and_slippage_bps=60))
    folds=_positive_folds(curve)
    passed,blockers=PortfolioProfitabilityGate().evaluate(metrics,positive_folds=folds,stress_total_return=stress["total_return"])
    return {"strategy":"stock_literature_momentum_v1","metrics":metrics,"positive_folds":folds,
            "stress_total_return":stress["total_return"],"numerical_gate_pass":passed,
            "blockers":list(blockers),"maximum_stock_weight":float(weights.max().max()),
            "average_exposure":float(weights.sum(axis=1).mean()),"cost_events":len(costs),
            "paper_approved":False}


if __name__ == "__main__": print(run())
