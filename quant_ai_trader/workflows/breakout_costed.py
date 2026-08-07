"""Evaluate fixed ATR breakout using observed Saxo SLV/EUR trading costs."""
from __future__ import annotations

import argparse

from quant_ai_trader.backtesting.backtester import BacktestConfig, ETFBacktester
from quant_ai_trader.backtesting.evaluation import ProfitabilityGate
from quant_ai_trader.config.settings import Settings
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.features.feature_pipeline import build_feature_dataset
from quant_ai_trader.strategies.breakout import breakout_signals


def run(symbol: str = "SLV") -> dict[str, object]:
    repository = MarketDataRepository(Settings().database_path)
    bars, spy = repository.load_bars(symbol), repository.load_bars("SPY")
    signals = breakout_signals(build_feature_dataset(bars, spy_bars=spy))
    base = ETFBacktester(config=BacktestConfig.saxo_us_etf_eur()).run(bars, signals)
    stress = ETFBacktester(config=BacktestConfig.saxo_us_etf_eur(stress_multiplier=2.0)).run(bars, signals)
    # Fold consistency must be recomputed with the same cost model. Fail closed
    # until that workflow supplies the value rather than borrowing old folds.
    fold_wins = 0
    approved, blockers = ProfitabilityGate().evaluate(base.metrics, fold_wins=fold_wins, stress_total_return=stress.metrics["total_return"])
    return {"symbol": symbol.upper(), "cost_model": {
        "minimum_commission_each_side": 1.0, "commission_bps": 8.0,
        "slippage_bps_each_side": 5.0, "fx_conversion_bps_each_side": 25.0,
    }, "metrics": base.metrics, "doubled_cost_total_return": stress.metrics["total_return"],
        "profitability_approved": approved, "blockers": list(blockers)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--symbol", default="SLV")
    print(run(parser.parse_args().symbol))
