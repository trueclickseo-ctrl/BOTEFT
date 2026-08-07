"""Exact-cost evaluation of the frozen, capped, consolidated 50/50 candidate."""
from __future__ import annotations

import pandas as pd

from quant_ai_trader.backtesting.evaluation import PortfolioProfitabilityGate
from quant_ai_trader.backtesting.weight_engine import WeightEngineConfig, run_weight_backtest
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.strategies.frozen_core_v2_blend import (
    FrozenCoreV2BlendConfig,
    build_frozen_core_v2_weights,
)
from quant_ai_trader.workflows.breakout_universe import DEFAULT_UNIVERSE
from quant_ai_trader.workflows.us_strategy_cost_audit import _positive_folds


def _target_turnover(weights: pd.DataFrame) -> float:
    return float(weights.diff().abs().sum(axis=1).sum())


def run(database_path="data/adjusted_total_return.sqlite3") -> dict:
    repository = MarketDataRepository(database_path)
    frames = {symbol: repository.load_bars(symbol) for symbol in DEFAULT_UNIVERSE}
    dates = sorted(set.intersection(*(set(frame.index) for frame in frames.values())))
    prices = pd.DataFrame(
        {symbol: frames[symbol].loc[dates, "adjusted_close"] for symbol in DEFAULT_UNIVERSE},
        index=dates,
    )
    strategy_config = FrozenCoreV2BlendConfig()
    weights, components = build_frozen_core_v2_weights(prices, strategy_config)
    asset_returns = prices.pct_change(fill_method=None).fillna(0.0)
    sleeve_returns = pd.DataFrame({
        name: (component * asset_returns).sum(axis=1)
        for name, component in components.items() if name != "unconstrained"
    })
    normal = WeightEngineConfig()
    stress = WeightEngineConfig(commission_bps=16, minimum_commission=2, fx_and_slippage_bps=60)
    curve, costs, metrics = run_weight_backtest(prices, weights, normal)
    stress_curve, stress_costs, stress_metrics = run_weight_backtest(prices, weights, stress)
    positive_folds = _positive_folds(curve)
    numerical_pass, blockers = PortfolioProfitabilityGate().evaluate(
        metrics,
        positive_folds=positive_folds,
        stress_total_return=stress_metrics["total_return"],
    )
    independent_target_turnover = sum(
        _target_turnover(component)
        for name, component in components.items()
        if name != "unconstrained"
    )
    consolidated_target_turnover = _target_turnover(weights)
    return {
        "strategy": "frozen_core_v2_50_50_consolidated",
        "rules": strategy_config.__dict__,
        "sample": {"start": str(prices.index[0].date()), "end": str(prices.index[-1].date())},
        "metrics": metrics,
        "positive_folds": positive_folds,
        "stress_total_return": stress_metrics["total_return"],
        "numerical_gate_pass": numerical_pass,
        "gate_blockers": list(blockers),
        "paper_approved": False,
        "paper_blockers": [
            "same_sample_selection_bias",
            "forward_validation_from_2026-08-08_not_yet_complete",
        ],
        "cash_yield_assumption": "zero_until_actual_saxo_eur_account_entitlement_is_verified",
        "average_invested_weight": float(weights.sum(axis=1).mean()),
        "average_cash_weight": float((1 - weights.sum(axis=1)).mean()),
        "sleeve_return_correlations": sleeve_returns.corr().round(6).to_dict(),
        "cap_binding_sessions": int(
            (components["unconstrained"].max(axis=1) > strategy_config.maximum_etf_weight + 1e-12).sum()
        ),
        "maximum_unconstrained_etf_weight": float(components["unconstrained"].max().max()),
        "maximum_consolidated_etf_weight": float(weights.max().max()),
        "independent_sleeve_target_turnover": independent_target_turnover,
        "consolidated_target_turnover": consolidated_target_turnover,
        "target_turnover_saved_by_netting": independent_target_turnover - consolidated_target_turnover,
        "cost_events": len(costs),
        "stress_cost_events": len(stress_costs),
        "latest_weights": {
            symbol: float(value) for symbol, value in weights.iloc[-1].items() if value > 0
        },
    }


if __name__ == "__main__":
    print(run())
