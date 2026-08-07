"""Unified corrected-cost audit for every implemented US ETF strategy family."""
from __future__ import annotations

import pandas as pd

from quant_ai_trader.backtesting.backtester import BacktestConfig, ETFBacktester
from quant_ai_trader.backtesting.blended_portfolio import blend_equity_curves
from quant_ai_trader.backtesting.cross_sectional import CrossSectionalConfig, run_cross_sectional_backtest
from quant_ai_trader.backtesting.diversified_core_satellite import DiversifiedCoreSatelliteConfig, run_diversified_core_satellite_backtest
from quant_ai_trader.backtesting.dual_momentum import (
    DualMomentumConfig, RiskTargetedDualMomentumConfig, run_dual_momentum_backtest,
    run_equal_weight_backtest, run_risk_targeted_dual_momentum_backtest,
    run_volatility_matched_equal_weight_backtest,
)
from quant_ai_trader.backtesting.evaluation import PortfolioProfitabilityGate, ProfitabilityGate
from quant_ai_trader.backtesting.momentum_low_vol import MomentumLowVolConfig, run_backtest as run_momentum_low_vol
from quant_ai_trader.backtesting.performance import calculate_performance
from quant_ai_trader.config.settings import Settings
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.features.feature_pipeline import build_feature_dataset
from quant_ai_trader.strategies.baselines import momentum_baseline_signals
from quant_ai_trader.strategies.breakout import breakout_signals
from quant_ai_trader.strategies.mean_reversion import rsi_mean_reversion_signals
from quant_ai_trader.strategies.multifactor import multifactor_trend_signals
from quant_ai_trader.strategies.trend_following import trend_following_signals
from quant_ai_trader.workflows.breakout_universe import DEFAULT_UNIVERSE


def _positive_folds(curve: pd.Series, folds: int = 4) -> int:
    start = int(len(curve) * .60); width = max((len(curve) - start) // folds, 1)
    positive = 0
    for fold in range(folds):
        left = start + fold * width
        right = start + (fold + 1) * width if fold < folds - 1 else len(curve)
        if right - left > 1 and curve.iloc[right - 1] / curve.iloc[left] - 1 > 0:
            positive += 1
    return positive


def _portfolio_row(name: str, curve: pd.Series, metrics: dict, stress_curve: pd.Series, stress_metrics: dict) -> dict:
    positive_folds = _positive_folds(curve)
    approved, blockers = PortfolioProfitabilityGate().evaluate(metrics, positive_folds=positive_folds, stress_total_return=stress_metrics["total_return"])
    return {"strategy": name, "symbol": "PORTFOLIO", "total_return": metrics["total_return"],
            "sharpe_ratio": metrics["sharpe_ratio"], "maximum_drawdown": metrics["maximum_drawdown"],
            "positive_folds": positive_folds, "stress_total_return": stress_metrics["total_return"],
            "approved": approved, "blockers": list(blockers)}


def run() -> dict[str, object]:
    repository = MarketDataRepository(Settings().database_path)
    bars = {symbol: repository.load_bars(symbol) for symbol in DEFAULT_UNIVERSE}
    spy = bars["SPY"]
    features = {symbol: build_feature_dataset(frame, spy_bars=spy) for symbol, frame in bars.items()}
    rows: list[dict[str, object]] = []
    signal_families = {
        "momentum_baseline": momentum_baseline_signals,
        "trend_following_v1": trend_following_signals,
        "rsi_mean_reversion_v1": rsi_mean_reversion_signals,
        "multifactor_trend_v1": multifactor_trend_signals,
        "atr_breakout_v1": breakout_signals,
    }
    for name, signal_function in signal_families.items():
        for symbol in DEFAULT_UNIVERSE:
            signals = signal_function(features[symbol])
            base = ETFBacktester(config=BacktestConfig.saxo_us_etf_eur()).run(bars[symbol], signals)
            stress = ETFBacktester(config=BacktestConfig.saxo_us_etf_eur(stress_multiplier=2)).run(bars[symbol], signals)
            positive_folds = _positive_folds(base.equity_curve)
            approved, blockers = ProfitabilityGate().evaluate(base.metrics, fold_wins=positive_folds, stress_total_return=stress.metrics["total_return"])
            rows.append({"strategy": name, "symbol": symbol, **base.metrics,
                         "positive_folds": positive_folds, "stress_total_return": stress.metrics["total_return"],
                         "approved": approved, "blockers": list(blockers)})

    normal_dm = DualMomentumConfig(trading_cost_bps=30, fixed_cost_per_order=1)
    stress_dm = DualMomentumConfig(trading_cost_bps=60, fixed_cost_per_order=2)
    curve, _, metrics = run_dual_momentum_backtest(bars, normal_dm)
    stress_curve, _, stress_metrics = run_dual_momentum_backtest(bars, stress_dm)
    rows.append(_portfolio_row("dual_momentum_rotation_v1", curve, metrics, stress_curve, stress_metrics))

    normal_rt = RiskTargetedDualMomentumConfig(trading_cost_bps=30, fixed_cost_per_order=1)
    stress_rt = RiskTargetedDualMomentumConfig(trading_cost_bps=60, fixed_cost_per_order=2)
    satellite, _, satellite_metrics = run_risk_targeted_dual_momentum_backtest(bars, normal_rt)
    stress_satellite, _, stress_satellite_metrics = run_risk_targeted_dual_momentum_backtest(bars, stress_rt)
    rows.append(_portfolio_row("risk_targeted_dual_momentum_v1", satellite, satellite_metrics, stress_satellite, stress_satellite_metrics))

    curve, _, metrics = run_cross_sectional_backtest(features, CrossSectionalConfig(trading_cost_bps=30))
    stress_curve, _, stress_metrics = run_cross_sectional_backtest(features, CrossSectionalConfig(trading_cost_bps=60))
    rows.append(_portfolio_row("regime_cross_sectional_v2_defensive", curve, metrics, stress_curve, stress_metrics))

    curve, _, metrics = run_momentum_low_vol(features, MomentumLowVolConfig(trading_cost_bps=30))
    stress_curve, _, stress_metrics = run_momentum_low_vol(features, MomentumLowVolConfig(trading_cost_bps=60))
    rows.append(_portfolio_row("momentum_low_vol_v1", curve, metrics, stress_curve, stress_metrics))

    curve, _, metrics = run_diversified_core_satellite_backtest(bars, DiversifiedCoreSatelliteConfig(trading_cost_bps=30))
    stress_curve, _, stress_metrics = run_diversified_core_satellite_backtest(bars, DiversifiedCoreSatelliteConfig(trading_cost_bps=60))
    rows.append(_portfolio_row("diversified_core_satellite_v1", curve, metrics, stress_curve, stress_metrics))

    core, _ = run_volatility_matched_equal_weight_backtest(bars, normal_rt)
    stress_core, _ = run_volatility_matched_equal_weight_backtest(bars, stress_rt)
    blend, blend_metrics = blend_equity_curves(core, satellite)
    stress_blend, stress_blend_metrics = blend_equity_curves(stress_core, stress_satellite)
    rows.append(_portfolio_row("core_satellite_v1", blend, blend_metrics, stress_blend, stress_blend_metrics))

    benchmark, benchmark_metrics = run_equal_weight_backtest(bars, trading_cost_bps=30)
    stress_benchmark, stress_benchmark_metrics = run_equal_weight_backtest(bars, trading_cost_bps=60)
    rows.append(_portfolio_row("equal_weight_benchmark", benchmark, benchmark_metrics, stress_benchmark, stress_benchmark_metrics))

    passed = [row for row in rows if row["approved"]]
    net_positive = [row for row in rows if row["total_return"] > 0]
    return {"cost_model": {"commission_bps": 8, "minimum_usd": 1, "fx_bps_each_side": 25,
                           "slippage_bps_each_side": 5, "stress_multiplier": 2},
            "evaluations": len(rows), "net_positive": len(net_positive), "approved": len(passed),
            "passed": passed, "best": sorted(rows, key=lambda row: (row["approved"], row["sharpe_ratio"], row["total_return"]), reverse=True)[:15],
            "not_evaluated": {"ai_target_stop": "No approved model artifact; previously rejected for weak OOS discrimination",
                              "ai_cross_sectional": "Rejected after leakage correction; no predictive edge"}}


if __name__ == "__main__": print(run())
