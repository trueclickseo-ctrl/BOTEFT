"""One-variable v2 test: continuous instead of binary SPY regime exposure."""
from quant_ai_trader.backtesting.defensive_momentum import DefensiveMomentumConfig, run_defensive_momentum_backtest
from quant_ai_trader.backtesting.evaluation import PortfolioProfitabilityGate
from quant_ai_trader.config.settings import Settings
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.workflows.breakout_universe import DEFAULT_UNIVERSE
from quant_ai_trader.workflows.us_vol_target_overlay_research import _fold_returns


def _evaluate(bars, width, stress=False):
    config = DefensiveMomentumConfig(
        holdings=8, target_annual_volatility=.10, trend_lookback_days=150,
        risk_adjusted_momentum_ranking=True, continuous_spy_regime_width=width,
        trading_cost_bps=60 if stress else 30, commission_bps=16 if stress else 8,
        fixed_cost_per_order=2 if stress else 1,
    )
    return run_defensive_momentum_backtest(bars, config)


def run():
    repository = MarketDataRepository(Settings().database_path)
    bars = {symbol: repository.load_bars(symbol) for symbol in DEFAULT_UNIVERSE}
    output = {}
    for name, width in (("risk_adjusted_binary_baseline", 0.0), ("linear_to_cash_at_minus_5_percent", .05)):
        curve, decisions, metrics = _evaluate(bars, width)
        _, _, stress = _evaluate(bars, width, stress=True)
        folds = _fold_returns(curve); positive = sum(value > 0 for value in folds)
        approved, blockers = PortfolioProfitabilityGate().evaluate(
            metrics, positive_folds=positive, stress_total_return=stress["total_return"])
        output[name] = {"metrics": metrics, "fold_returns": folds, "positive_folds": positive,
                        "stress_total_return": stress["total_return"], "approved": approved,
                        "blockers": list(blockers), "membership_changes": int(decisions.membership_changes.sum()),
                        "partially_invested_rebalances": int(decisions.spy_regime_multiplier.between(0, 1, inclusive="neither").sum())}
    return output


if __name__ == "__main__": print(run())
