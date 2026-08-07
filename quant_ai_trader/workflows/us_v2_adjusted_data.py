"""Frozen v2 comparisons across Saxo price-only and Yahoo adjusted datasets."""
from pathlib import Path

from quant_ai_trader.backtesting.defensive_momentum import DefensiveMomentumConfig, run_defensive_momentum_backtest
from quant_ai_trader.backtesting.evaluation import PortfolioProfitabilityGate
from quant_ai_trader.config.settings import Settings
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.workflows.breakout_universe import DEFAULT_UNIVERSE
from quant_ai_trader.workflows.us_v2_expanded_universe import ADDITIONS
from quant_ai_trader.workflows.us_vol_target_overlay_research import _fold_returns


ADJUSTED_DATABASE = Path("data/adjusted_total_return.sqlite3")
EXPANDED_UNIVERSE = DEFAULT_UNIVERSE + ("IEF",) + ADDITIONS


def _evaluate(bars, stress=False):
    config = DefensiveMomentumConfig(
        holdings=8, target_annual_volatility=.10, trend_lookback_days=150,
        risk_adjusted_momentum_ranking=True,
        trading_cost_bps=60 if stress else 30, commission_bps=16 if stress else 8,
        fixed_cost_per_order=2 if stress else 1,
    )
    return run_defensive_momentum_backtest(bars, config)


def _result(bars):
    curve, decisions, metrics = _evaluate(bars)
    _, _, stress = _evaluate(bars, stress=True)
    folds = _fold_returns(curve); positive = sum(value > 0 for value in folds)
    approved, blockers = PortfolioProfitabilityGate().evaluate(
        metrics, positive_folds=positive, stress_total_return=stress["total_return"])
    return {"metrics": metrics, "fold_returns": folds, "positive_folds": positive,
            "stress_total_return": stress["total_return"], "approved": approved,
            "blockers": list(blockers), "membership_changes": int(decisions.membership_changes.sum())}


def _aligned(repositories, symbols):
    collections = [{symbol: repository.load_bars(symbol) for symbol in symbols} for repository in repositories]
    common = sorted(set.intersection(*(set(frame.index) for collection in collections for frame in collection.values())))
    return [{symbol: frame.loc[common] for symbol, frame in collection.items()} for collection in collections], common


def run():
    saxo = MarketDataRepository(Settings().database_path)
    adjusted = MarketDataRepository(ADJUSTED_DATABASE)
    (saxo14, adjusted14), common14 = _aligned((saxo, adjusted), DEFAULT_UNIVERSE)
    (adjusted14_expanded_sample, adjusted20), common20 = _aligned((adjusted, adjusted), EXPANDED_UNIVERSE)
    adjusted14_expanded_sample = {symbol: adjusted14_expanded_sample[symbol] for symbol in DEFAULT_UNIVERSE}
    return {
        "source_comparison_period": (str(common14[0].date()), str(common14[-1].date())),
        "saxo_price_only_14": _result(saxo14),
        "yahoo_adjusted_14": _result(adjusted14),
        "universe_comparison_period": (str(common20[0].date()), str(common20[-1].date())),
        "yahoo_adjusted_14_common": _result(adjusted14_expanded_sample),
        "yahoo_adjusted_20": _result(adjusted20),
    }


if __name__ == "__main__": print(run())
