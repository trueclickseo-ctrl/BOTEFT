"""Four-fold, exact-cost evaluation of the layered US ETF momentum v3."""
import pandas as pd

from quant_ai_trader.backtesting.evaluation import PortfolioProfitabilityGate
from quant_ai_trader.backtesting.weight_engine import WeightEngineConfig, run_weight_backtest
from quant_ai_trader.config.settings import Settings
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.risk.tail_relative_strength import tail_risk_multiplier
from quant_ai_trader.strategies.us_etf_momentum_v3 import MomentumV3Config, base_weights, build_strategy_weights
from quant_ai_trader.workflows.us_vol_target_overlay_research import _fold_returns


V3_UNIVERSE = ("SPY", "QQQ", "IWM", "XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "TLT", "GLD")


def _result(prices, weights, cost):
    curve, costs, metrics = run_weight_backtest(prices, weights, cost)
    folds = _fold_returns(curve); positive = sum(value > 0 for value in folds)
    return curve, {"metrics": metrics, "fold_returns": folds, "positive_folds": positive,
                   "cost_events": len(costs)}


def run():
    repository = MarketDataRepository(Settings().database_path)
    frames = {symbol: repository.load_bars(symbol) for symbol in V3_UNIVERSE}
    dates = sorted(set.intersection(*(set(frame.index) for frame in frames.values())))
    prices = pd.DataFrame({symbol: frames[symbol].loc[dates, "adjusted_close"] for symbol in V3_UNIVERSE}, index=dates)
    strategy_config = MomentumV3Config()
    base = base_weights(prices, strategy_config)
    asset_returns = prices.pct_change(fill_method=None).fillna(0.0)
    base_returns = (base * asset_returns).sum(axis=1)
    multiplier = tail_risk_multiplier(base_returns)
    overlaid = build_strategy_weights(prices, multiplier, strategy_config)
    normal = WeightEngineConfig(); stress = WeightEngineConfig(commission_bps=16, minimum_commission=2,
                                                                fx_and_slippage_bps=60)
    base_curve, base_result = _result(prices, base, normal)
    _, base_stress = _result(prices, base, stress)
    overlay_curve, overlay_result = _result(prices, overlaid, normal)
    _, overlay_stress = _result(prices, overlaid, stress)
    for result, stress_result in ((base_result, base_stress), (overlay_result, overlay_stress)):
        result["stress_total_return"] = stress_result["metrics"]["total_return"]
        approved, blockers = PortfolioProfitabilityGate().evaluate(
            result["metrics"], positive_folds=result["positive_folds"],
            stress_total_return=result["stress_total_return"])
        result.update({"approved": approved, "blockers": list(blockers)})
    return {"strategy": "us_etf_momentum_v3", "universe": V3_UNIVERSE,
            "universe_note": "Uses 12 currently stored approved instruments; XLB is not yet in BOTEF data.",
            "rules": strategy_config.__dict__, "base": base_result, "tail_overlay": overlay_result,
            "tail_reduced_sessions": int((multiplier < 1).sum()),
            "tail_transitions": int((multiplier.diff().fillna(0) != 0).sum())}


if __name__ == "__main__": print(run())
