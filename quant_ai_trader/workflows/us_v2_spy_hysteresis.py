"""One-variable v2 test: stateful SPY regime hysteresis at rebalance dates."""
from quant_ai_trader.backtesting.defensive_momentum import DefensiveMomentumConfig, run_defensive_momentum_backtest
from quant_ai_trader.backtesting.evaluation import PortfolioProfitabilityGate
from quant_ai_trader.config.settings import Settings
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.workflows.breakout_universe import DEFAULT_UNIVERSE
from quant_ai_trader.workflows.us_vol_target_overlay_research import _fold_returns


def _evaluate(bars, hysteresis, stress=False):
    config = DefensiveMomentumConfig(
        holdings=8, target_annual_volatility=.10, trend_lookback_days=150,
        risk_adjusted_momentum_ranking=True, spy_regime_hysteresis=hysteresis,
        trading_cost_bps=60 if stress else 30, commission_bps=16 if stress else 8,
        fixed_cost_per_order=2 if stress else 1,
    )
    return run_defensive_momentum_backtest(bars, config)


def run():
    repository = MarketDataRepository(Settings().database_path)
    bars = {symbol: repository.load_bars(symbol) for symbol in DEFAULT_UNIVERSE}
    output = {}
    for name, band in (("risk_adjusted_baseline", 0.0), ("two_percent_spy_hysteresis", .02)):
        curve, decisions, metrics = _evaluate(bars, band)
        _, _, stress = _evaluate(bars, band, stress=True)
        folds = _fold_returns(curve); positive = sum(value > 0 for value in folds)
        approved, blockers = PortfolioProfitabilityGate().evaluate(
            metrics, positive_folds=positive, stress_total_return=stress["total_return"])
        output[name] = {"metrics": metrics, "fold_returns": folds, "positive_folds": positive,
                        "stress_total_return": stress["total_return"], "approved": approved,
                        "blockers": list(blockers), "membership_changes": int(decisions.membership_changes.sum()),
                        "regime_transitions": int((decisions.risk_on != decisions.risk_on.shift()).sum() - 1),
                        "regime_exits": int(decisions.regime_exits.sum())}
    return output


if __name__ == "__main__": print(run())
