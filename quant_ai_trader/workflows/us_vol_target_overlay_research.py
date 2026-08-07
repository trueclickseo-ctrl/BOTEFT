"""Cost-inclusive v2 versus weekly, thresholded volatility overlay."""
from quant_ai_trader.backtesting.defensive_momentum import DefensiveMomentumConfig, run_defensive_momentum_backtest
from quant_ai_trader.backtesting.evaluation import PortfolioProfitabilityGate
from quant_ai_trader.config.settings import Settings
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.workflows.breakout_universe import DEFAULT_UNIVERSE
from quant_ai_trader.workflows.us_strategy_cost_audit import _positive_folds


def _fold_returns(curve, folds=4):
    start = int(len(curve) * .60)
    width = max((len(curve) - start) // folds, 1)
    values = []
    for fold in range(folds):
        left = start + fold * width
        right = start + (fold + 1) * width if fold < folds - 1 else len(curve)
        values.append(float(curve.iloc[right - 1] / curve.iloc[left] - 1))
    return values


def _evaluate(bars, config, stress_config):
    curve, _, metrics = run_defensive_momentum_backtest(bars, config)
    _, _, stress = run_defensive_momentum_backtest(bars, stress_config)
    folds = _positive_folds(curve)
    approved, blockers = PortfolioProfitabilityGate().evaluate(metrics, positive_folds=folds,
                                                                stress_total_return=stress["total_return"])
    return {"metrics": metrics, "fold_returns": _fold_returns(curve), "positive_folds": folds,
            "stress_total_return": stress["total_return"],
            "approved": approved, "blockers": list(blockers)}


def run():
    repository = MarketDataRepository(Settings().database_path)
    bars = {symbol: repository.load_bars(symbol) for symbol in DEFAULT_UNIVERSE}
    common = dict(holdings=8, target_annual_volatility=.10, trend_lookback_days=150)
    baseline = _evaluate(bars, DefensiveMomentumConfig(**common),
                         DefensiveMomentumConfig(**common, trading_cost_bps=60, commission_bps=16, fixed_cost_per_order=2))
    overlay = _evaluate(bars, DefensiveMomentumConfig(**common, dynamic_vol_targeting=True),
                        DefensiveMomentumConfig(**common, dynamic_vol_targeting=True,
                                                trading_cost_bps=60, commission_bps=16, fixed_cost_per_order=2))
    return {"strategy": "defensive_momentum_v2_weekly_vol_overlay", "account_currency": "EUR",
            "variable_cost_bps_per_weight_change": 30, "commission_bps": 8,
            "minimum_commission_usd": 1, "stress_multiplier": 2,
            "baseline": baseline, "weekly_threshold_overlay": overlay}


if __name__ == "__main__": print(run())
