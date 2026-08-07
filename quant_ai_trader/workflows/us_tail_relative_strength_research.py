"""Exact-cost comparison of lower-turnover tail and relative-strength variants."""
from quant_ai_trader.backtesting.defensive_momentum import DefensiveMomentumConfig, run_defensive_momentum_backtest
from quant_ai_trader.backtesting.evaluation import PortfolioProfitabilityGate
from quant_ai_trader.config.settings import Settings
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.workflows.breakout_universe import DEFAULT_UNIVERSE
from quant_ai_trader.workflows.us_vol_target_overlay_research import _fold_returns


def _evaluate(bars, config):
    curve, _, metrics = run_defensive_momentum_backtest(bars, config)
    stress_config = DefensiveMomentumConfig(**(config.__dict__ | {
        "trading_cost_bps": 60, "commission_bps": 16, "fixed_cost_per_order": 2
    }))
    _, _, stress = run_defensive_momentum_backtest(bars, stress_config)
    folds = _fold_returns(curve)
    positive = sum(value > 0 for value in folds)
    approved, blockers = PortfolioProfitabilityGate().evaluate(
        metrics, positive_folds=positive, stress_total_return=stress["total_return"]
    )
    return {"metrics": metrics, "fold_returns": folds, "positive_folds": positive,
            "stress_total_return": stress["total_return"], "approved": approved,
            "blockers": list(blockers)}


def run():
    repository = MarketDataRepository(Settings().database_path)
    bars = {symbol: repository.load_bars(symbol) for symbol in DEFAULT_UNIVERSE}
    baseline = dict(holdings=8, target_annual_volatility=.10, trend_lookback_days=150)
    relative = dict(momentum_lookback_days=126, skip_recent_days=21, holdings=5,
                    rebalance_days=5, equal_weight_selection=True,
                    target_annual_volatility=.10, trend_lookback_days=150)
    return {
        "cost_model": {"account_currency": "EUR", "commission_bps": 8, "minimum_usd": 1,
                       "fx_and_slippage_bps": 30, "stress_multiplier": 2},
        "baseline_v2": _evaluate(bars, DefensiveMomentumConfig(**baseline)),
        "tail_only": _evaluate(bars, DefensiveMomentumConfig(**baseline, tail_risk_enabled=True)),
        "relative_strength_only": _evaluate(bars, DefensiveMomentumConfig(**relative)),
        "relative_strength_plus_tail": _evaluate(bars, DefensiveMomentumConfig(**relative, tail_risk_enabled=True)),
    }


if __name__ == "__main__": print(run())
