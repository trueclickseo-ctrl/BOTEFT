"""Costed, no-look-ahead defensive momentum portfolio research backtest."""
from __future__ import annotations

from dataclasses import dataclass
import math
import pandas as pd

from quant_ai_trader.backtesting.performance import calculate_performance


@dataclass(frozen=True)
class DefensiveMomentumConfig:
    initial_cash: float = 100_000.0
    momentum_lookback_days: int = 252
    trend_lookback_days: int = 200
    volatility_lookback_days: int = 60
    rebalance_days: int = 21
    holdings: int = 3
    target_annual_volatility: float = .08
    maximum_etf_weight: float = .10
    require_asset_uptrend: bool = True
    trading_cost_bps: float = 30.0
    commission_bps: float = 8.0
    fixed_cost_per_order: float = 1.0
    dynamic_vol_targeting: bool = False
    resize_days: int = 5
    resize_threshold: float = .02
    overlay_volatility_window: int = 20
    overlay_target_volatility: float = .10
    overlay_volatility_floor: float = .05
    overlay_max_leverage: float = 1.5
    risk_off_multiplier: float = .30
    skip_recent_days: int = 0
    equal_weight_selection: bool = False
    tail_risk_enabled: bool = False
    tail_dd_threshold: float = -.05
    tail_vol_window: int = 20
    tail_vol_zscore_threshold: float = 1.5
    tail_vol_lookback: int = 252
    tail_cut_exposure: float = .30
    tail_cooldown_days: int = 10


def run_defensive_momentum_backtest(
    price_frames: dict[str, pd.DataFrame],
    config: DefensiveMomentumConfig = DefensiveMomentumConfig(),
) -> tuple[pd.Series, pd.DataFrame, dict[str, float]]:
    if "SPY" not in price_frames:
        raise ValueError("SPY is required for the defensive regime filter")
    symbols = sorted(price_frames)
    dates = sorted(set.intersection(*(set(frame.index) for frame in price_frames.values())))
    required = max(config.momentum_lookback_days + config.skip_recent_days,
                   config.trend_lookback_days, config.volatility_lookback_days)
    if len(dates) <= required + 1:
        raise ValueError("Insufficient common history for defensive momentum")
    prices = pd.DataFrame({symbol: price_frames[symbol].loc[dates, "adjusted_close"] for symbol in symbols}, index=dates)
    returns = prices.pct_change(fill_method=None).fillna(0.0)
    equity = config.initial_cash
    weights = pd.Series(0.0, index=symbols)
    base_weights = weights.copy()
    curve, decisions = [], []
    total_turnover, total_orders, resize_count = 0.0, 0, 0
    tail_multiplier, tail_clean_days, tail_transition_count = 1.0, config.tail_cooldown_days, 0

    def trade_to(desired: pd.Series) -> tuple[float, int]:
        nonlocal equity, weights, total_turnover, total_orders
        changes = (desired - weights).abs()
        turnover = float(changes.sum())
        order_count = int((changes > 1e-12).sum())
        pretrade_equity = equity
        variable_cost = pretrade_equity * turnover * config.trading_cost_bps / 10_000
        commissions = sum(max(pretrade_equity * float(change) * config.commission_bps / 10_000,
                              config.fixed_cost_per_order)
                          for change in changes[changes > 1e-12])
        equity = max(equity - variable_cost - commissions, 0.0)
        weights = desired
        total_turnover += turnover
        total_orders += order_count
        return turnover, order_count

    for i, date in enumerate(dates):
        if i > 0:
            equity *= max(1.0 + float((weights * returns.iloc[i]).sum()), 0.0)
        if i > required and (i - required - 1) % config.rebalance_days == 0:
            signal = i - 1
            new_weights = pd.Series(0.0, index=symbols)
            spy_risk_on = prices.iloc[signal]["SPY"] > prices["SPY"].iloc[signal-config.trend_lookback_days+1:signal+1].mean()
            momentum_end = signal - config.skip_recent_days
            momentum = prices.iloc[momentum_end] / prices.iloc[momentum_end-config.momentum_lookback_days] - 1
            asset_uptrend = prices.iloc[signal] > prices.iloc[signal-config.trend_lookback_days+1:signal+1].mean()
            eligible_mask = (momentum > 0) & (asset_uptrend if config.require_asset_uptrend else True)
            eligible = momentum[eligible_mask].nlargest(config.holdings) if spy_risk_on else pd.Series(dtype=float)
            if len(eligible):
                asset_vol = returns[list(eligible.index)].iloc[signal-config.volatility_lookback_days+1:signal+1].std(ddof=1) * math.sqrt(252)
                inverse_vol = (1 / asset_vol.replace(0, float("nan"))).dropna()
                raw = pd.Series(1 / len(eligible), index=eligible.index) if config.equal_weight_selection else (inverse_vol / inverse_vol.sum() if inverse_vol.sum() > 0 else inverse_vol)
                covariance = returns[list(raw.index)].iloc[signal-config.volatility_lookback_days+1:signal+1].cov() * 252
                portfolio_vol = float(math.sqrt(max(raw @ covariance @ raw, 0.0)))
                scale = min(1.0, config.target_annual_volatility / portfolio_vol) if portfolio_vol > 0 else 0.0
                new_weights.loc[raw.index] = (raw * scale).clip(upper=config.maximum_etf_weight)
            base_weights = new_weights
            target = base_weights * tail_multiplier
            turnover, order_count = (0.0, 0) if config.dynamic_vol_targeting else trade_to(target)
            decisions.append({"date": date, "signal_date": dates[signal], "risk_on": spy_risk_on,
                              "holdings": int((base_weights > 0).sum()), "exposure": float(base_weights.sum()),
                              "turnover": turnover, "order_count": order_count})
        if config.dynamic_vol_targeting and i >= config.overlay_volatility_window and i % config.resize_days == 0:
            trailing = returns.iloc[i-config.overlay_volatility_window+1:i+1]
            vol = (trailing.std(ddof=1) * math.sqrt(252)).clip(lower=config.overlay_volatility_floor)
            scale = (config.overlay_target_volatility / vol).clip(upper=config.overlay_max_leverage)
            regime_on = prices.iloc[i]["SPY"] > prices["SPY"].iloc[i-config.trend_lookback_days+1:i+1].mean() if i >= config.trend_lookback_days else False
            regime_multiplier = 1.0 if regime_on else config.risk_off_multiplier
            desired = (base_weights * scale * regime_multiplier).clip(upper=config.maximum_etf_weight)
            desired[(desired - weights).abs() < config.resize_threshold] = weights
            turnover, order_count = trade_to(desired)
            if turnover > 0:
                resize_count += 1
        if config.tail_risk_enabled and len(curve) >= config.tail_vol_window + config.tail_vol_lookback:
            provisional = pd.Series(curve + [equity])
            strategy_returns = provisional.pct_change(fill_method=None).fillna(0.0)
            dd = float(provisional.iloc[-1] / provisional.cummax().iloc[-1] - 1)
            vol = strategy_returns.rolling(config.tail_vol_window).std(ddof=1)
            history = vol.iloc[-config.tail_vol_lookback:]
            vol_std = float(history.std(ddof=1))
            vol_z = (float(vol.iloc[-1]) - float(history.mean())) / vol_std if vol_std > 0 else 0.0
            triggered = dd < config.tail_dd_threshold and vol_z > config.tail_vol_zscore_threshold
            old_multiplier = tail_multiplier
            if triggered:
                tail_multiplier, tail_clean_days = config.tail_cut_exposure, 0
            elif tail_multiplier < 1:
                tail_clean_days += 1
                if tail_clean_days >= config.tail_cooldown_days:
                    tail_multiplier = 1.0
            if tail_multiplier != old_multiplier:
                trade_to(base_weights * tail_multiplier)
                tail_transition_count += 1
        curve.append(equity)
    equity_curve = pd.Series(curve, index=dates, name="equity")
    metrics = calculate_performance(equity_curve, pd.DataFrame())
    metrics["rebalance_count"] = float(len(decisions))
    metrics["average_exposure"] = float(pd.DataFrame(decisions)["exposure"].mean()) if decisions else 0.0
    metrics["total_turnover"] = total_turnover
    metrics["annualized_turnover"] = total_turnover / (len(dates) / 252)
    metrics["order_count"] = float(total_orders)
    metrics["resize_count"] = float(resize_count)
    metrics["tail_transition_count"] = float(tail_transition_count)
    return equity_curve, pd.DataFrame(decisions), metrics
