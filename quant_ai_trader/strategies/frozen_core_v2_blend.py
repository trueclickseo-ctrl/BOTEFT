"""Frozen 50/50 core-satellite and defensive-momentum v2 portfolio weights."""
from __future__ import annotations

from dataclasses import dataclass
import math

import pandas as pd


@dataclass(frozen=True)
class FrozenCoreV2BlendConfig:
    core_equal_weight_allocation: float = .25
    dual_momentum_allocation: float = .25
    defensive_v2_allocation: float = .50
    maximum_etf_weight: float = .10
    rebalance_days: int = 21
    momentum_lookback_days: int = 252
    trend_lookback_days: int = 150
    defensive_volatility_lookback_days: int = 60
    sleeve_volatility_lookback_days: int = 20
    target_annual_volatility: float = .10
    defensive_holdings: int = 8

    def __post_init__(self):
        total = (self.core_equal_weight_allocation + self.dual_momentum_allocation
                 + self.defensive_v2_allocation)
        if not math.isclose(total, 1.0):
            raise ValueError("Frozen sleeve allocations must sum to one")
        if not 0 < self.maximum_etf_weight <= 1:
            raise ValueError("maximum_etf_weight must be in (0, 1]")


def _validate_prices(prices: pd.DataFrame, require_spy: bool = True) -> pd.DataFrame:
    if prices.empty or (require_spy and "SPY" not in prices):
        raise ValueError("Non-empty prices including SPY are required")
    if prices.isna().any().any() or (prices <= 0).any().any():
        raise ValueError("Prices must be aligned, positive, and complete")
    return prices.astype(float)


def _core_equal_weight_weights(prices: pd.DataFrame, config: FrozenCoreV2BlendConfig) -> pd.DataFrame:
    returns = prices.pct_change(fill_method=None)
    basket_returns = returns.mean(axis=1)
    output = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    current = pd.Series(0.0, index=prices.columns)
    lookback = config.sleeve_volatility_lookback_days
    for i, date in enumerate(prices.index):
        output.loc[date] = current
        if i > lookback and (i - lookback - 1) % config.rebalance_days == 0:
            signal_returns = basket_returns.iloc[i-lookback:i]
            volatility = float(signal_returns.std(ddof=1) * math.sqrt(252))
            exposure = min(1.0, config.target_annual_volatility / volatility) if volatility > 0 else 0.0
            current = pd.Series(
                config.core_equal_weight_allocation * exposure / len(prices.columns),
                index=prices.columns,
            )
    return output


def _dual_momentum_weights(prices: pd.DataFrame, config: FrozenCoreV2BlendConfig) -> pd.DataFrame:
    returns = prices.pct_change(fill_method=None)
    output = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    current = pd.Series(0.0, index=prices.columns)
    lookback = config.momentum_lookback_days
    vol_lookback = config.sleeve_volatility_lookback_days
    for i, date in enumerate(prices.index):
        output.loc[date] = current
        if i > lookback and (i - lookback - 1) % config.rebalance_days == 0:
            signal = i - 1
            momentum = prices.iloc[signal] / prices.iloc[signal-lookback] - 1
            selected = momentum.idxmax() if momentum.max() > 0 else None
            current = pd.Series(0.0, index=prices.columns)
            if selected is not None:
                volatility = float(
                    returns[selected].iloc[signal-vol_lookback+1:signal+1].std(ddof=1)
                    * math.sqrt(252)
                )
                exposure = min(1.0, config.target_annual_volatility / volatility) if volatility > 0 else 0.0
                current.loc[selected] = config.dual_momentum_allocation * exposure
    return output


def _defensive_v2_weights(prices: pd.DataFrame, config: FrozenCoreV2BlendConfig) -> pd.DataFrame:
    if config.defensive_v2_allocation == 0:
        return pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    returns = prices.pct_change(fill_method=None)
    output = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    current = pd.Series(0.0, index=prices.columns)
    required = max(config.momentum_lookback_days, config.trend_lookback_days,
                   config.defensive_volatility_lookback_days)
    for i, date in enumerate(prices.index):
        output.loc[date] = current
        if i > required and (i - required - 1) % config.rebalance_days == 0:
            signal = i - 1
            current = pd.Series(0.0, index=prices.columns)
            spy_ma = prices["SPY"].iloc[signal-config.trend_lookback_days+1:signal+1].mean()
            if prices.iloc[signal]["SPY"] <= spy_ma:
                continue
            momentum = prices.iloc[signal] / prices.iloc[signal-config.momentum_lookback_days] - 1
            asset_ma = prices.iloc[signal-config.trend_lookback_days+1:signal+1].mean()
            eligible = (momentum > 0) & (prices.iloc[signal] > asset_ma)
            ranking_vol = (
                returns.iloc[signal-config.momentum_lookback_days+1:signal+1].std(ddof=1)
                * math.sqrt(252)
            )
            score = (momentum / ranking_vol.replace(0, float("nan")))[eligible].dropna()
            selected = score.nlargest(config.defensive_holdings).index
            if selected.empty:
                continue
            asset_vol = (
                returns[list(selected)].iloc[
                    signal-config.defensive_volatility_lookback_days+1:signal+1
                ].std(ddof=1) * math.sqrt(252)
            )
            inverse_vol = (1 / asset_vol.replace(0, float("nan"))).dropna()
            if inverse_vol.empty or inverse_vol.sum() <= 0:
                continue
            raw = inverse_vol / inverse_vol.sum()
            covariance = returns[list(raw.index)].iloc[
                signal-config.defensive_volatility_lookback_days+1:signal+1
            ].cov() * 252
            portfolio_vol = float(math.sqrt(max(raw @ covariance @ raw, 0.0)))
            scale = min(1.0, config.target_annual_volatility / portfolio_vol) if portfolio_vol > 0 else 0.0
            sleeve_weights = (raw * scale).clip(upper=config.maximum_etf_weight)
            current.loc[sleeve_weights.index] = sleeve_weights * config.defensive_v2_allocation
    return output


def build_frozen_core_v2_weights(
    prices: pd.DataFrame,
    config: FrozenCoreV2BlendConfig = FrozenCoreV2BlendConfig(),
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Net three frozen sleeves by symbol, enforce the portfolio cap, and retain cash."""
    prices = _validate_prices(prices, require_spy=config.defensive_v2_allocation > 0)
    components = {
        "core_equal_weight": _core_equal_weight_weights(prices, config),
        "dual_momentum": _dual_momentum_weights(prices, config),
        "defensive_v2": _defensive_v2_weights(prices, config),
    }
    unconstrained = sum(components.values(), start=pd.DataFrame(
        0.0, index=prices.index, columns=prices.columns
    ))
    consolidated = unconstrained.clip(lower=0.0, upper=config.maximum_etf_weight)
    if (consolidated.sum(axis=1) > 1 + 1e-12).any():
        raise ValueError("Consolidated weights exceed available capital")
    components["unconstrained"] = unconstrained
    return consolidated, components
