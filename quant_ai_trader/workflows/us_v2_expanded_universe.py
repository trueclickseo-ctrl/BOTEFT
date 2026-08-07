"""One-variable v2 test: current 14 versus predeclared 19-ETF universe."""
from pathlib import Path

from quant_ai_trader.backtesting.defensive_momentum import DefensiveMomentumConfig, run_defensive_momentum_backtest
from quant_ai_trader.backtesting.evaluation import PortfolioProfitabilityGate
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.workflows.breakout_universe import DEFAULT_UNIVERSE
from quant_ai_trader.workflows.us_vol_target_overlay_research import _fold_returns


ADDITIONS = ("TIP", "PDBC", "EFA", "EEM", "VNQ")
EXPANDED_UNIVERSE = DEFAULT_UNIVERSE + ADDITIONS
EXPANDED_DATABASE = Path("data/expanded_universe.sqlite3")


def _evaluate(bars, stress=False):
    config = DefensiveMomentumConfig(
        holdings=8, target_annual_volatility=.10, trend_lookback_days=150,
        risk_adjusted_momentum_ranking=True,
        trading_cost_bps=60 if stress else 30, commission_bps=16 if stress else 8,
        fixed_cost_per_order=2 if stress else 1,
    )
    return run_defensive_momentum_backtest(bars, config)


def run():
    repository = MarketDataRepository(EXPANDED_DATABASE)
    all_bars = {symbol: repository.load_bars(symbol) for symbol in EXPANDED_UNIVERSE}
    common_dates = sorted(set.intersection(*(set(frame.index) for frame in all_bars.values())))
    if not common_dates:
        raise ValueError("Expanded universe has no common history")
    all_bars = {symbol: frame.loc[common_dates] for symbol, frame in all_bars.items()}
    output = {"data_convention": "Saxo price-only; dividends are not adjusted",
              "common_start": str(common_dates[0].date()), "common_end": str(common_dates[-1].date()),
              "excluded": {"IEF": "Only Saxo listing starts 2017-08-02; fails 2014+ predeclaration"}}
    for name, universe in (("current_14", DEFAULT_UNIVERSE), ("expanded_19", EXPANDED_UNIVERSE)):
        bars = {symbol: all_bars[symbol] for symbol in universe}
        curve, decisions, metrics = _evaluate(bars)
        _, _, stress = _evaluate(bars, stress=True)
        folds = _fold_returns(curve); positive = sum(value > 0 for value in folds)
        approved, blockers = PortfolioProfitabilityGate().evaluate(
            metrics, positive_folds=positive, stress_total_return=stress["total_return"])
        output[name] = {"universe": universe, "metrics": metrics, "fold_returns": folds,
                        "positive_folds": positive, "stress_total_return": stress["total_return"],
                        "approved": approved, "blockers": list(blockers),
                        "membership_changes": int(decisions.membership_changes.sum())}
    return output


if __name__ == "__main__": print(run())
