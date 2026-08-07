"""Exact-cost comparison of v2 with an existing-position-only no-trade band."""
from quant_ai_trader.backtesting.defensive_momentum import DefensiveMomentumConfig, run_defensive_momentum_backtest
from quant_ai_trader.backtesting.evaluation import PortfolioProfitabilityGate
from quant_ai_trader.config.settings import Settings
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.workflows.breakout_universe import DEFAULT_UNIVERSE
from quant_ai_trader.workflows.us_vol_target_overlay_research import _fold_returns


def _evaluate(bars, threshold, stress=False):
    config = DefensiveMomentumConfig(holdings=8, target_annual_volatility=.10, trend_lookback_days=150,
        existing_position_rebalance_threshold=threshold, trading_cost_bps=60 if stress else 30,
        commission_bps=16 if stress else 8, fixed_cost_per_order=2 if stress else 1)
    curve, decisions, metrics = run_defensive_momentum_backtest(bars, config)
    folds = _fold_returns(curve)
    return metrics, folds, decisions


def run():
    repository = MarketDataRepository(Settings().database_path)
    bars = {symbol: repository.load_bars(symbol) for symbol in DEFAULT_UNIVERSE}
    output = {}
    for name, threshold in (("baseline", 0.0), ("one_percent_existing_position_band", .01)):
        metrics, folds, decisions = _evaluate(bars, threshold)
        stress, _, _ = _evaluate(bars, threshold, stress=True)
        positive = sum(value > 0 for value in folds)
        approved, blockers = PortfolioProfitabilityGate().evaluate(
            metrics, positive_folds=positive, stress_total_return=stress["total_return"])
        output[name] = {"metrics": metrics, "fold_returns": folds, "positive_folds": positive,
                        "stress_total_return": stress["total_return"], "approved": approved,
                        "blockers": list(blockers), "small_resize_orders": int(decisions.small_resize_orders.sum())}
    return output


if __name__ == "__main__": print(run())
