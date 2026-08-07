"""No-look-ahead monthly dual-momentum portfolio backtest."""

from __future__ import annotations
from dataclasses import dataclass
import math
import pandas as pd
from quant_ai_trader.backtesting.performance import calculate_performance


@dataclass(frozen=True)
class DualMomentumConfig:
    initial_cash: float = 100_000.0
    lookback_days: int = 252
    rebalance_days: int = 21
    trading_cost_bps: float = 5.0


@dataclass(frozen=True)
class RiskTargetedDualMomentumConfig(DualMomentumConfig):
    target_annual_volatility: float = 0.10
    volatility_lookback_days: int = 20


def run_dual_momentum_backtest(price_frames: dict[str, pd.DataFrame], config: DualMomentumConfig = DualMomentumConfig()) -> tuple[pd.Series, pd.DataFrame, dict[str, float]]:
    """Hold the strongest ETF with positive trailing momentum, otherwise cash."""
    if not price_frames:
        raise ValueError("At least one ETF price frame is required")
    symbols = sorted(price_frames)
    dates = sorted(set.intersection(*(set(frame.index) for frame in price_frames.values())))
    if len(dates) <= config.lookback_days + 1:
        raise ValueError("Insufficient common history for dual momentum lookback")
    prices = pd.DataFrame({symbol: price_frames[symbol].loc[dates, "adjusted_close"] for symbol in symbols}, index=dates)
    equity, holding, curve, decisions = config.initial_cash, None, [], []
    for i, date in enumerate(dates):
        if i > 0 and holding is not None:
            equity *= prices.loc[date, holding] / prices.iloc[i - 1][holding]
        # Signals end at i-1, so one additional completed session is required
        # beyond the lookback window before the first position can be held.
        if i > config.lookback_days and (i - config.lookback_days - 1) % config.rebalance_days == 0:
            signal_date = dates[i - 1]
            returns = prices.iloc[i - 1] / prices.iloc[i - 1 - config.lookback_days] - 1
            selected = returns.idxmax() if returns.max() > 0 else None
            turnover = float(selected != holding)
            equity *= 1 - turnover * config.trading_cost_bps / 10_000
            holding = selected
            decisions.append({"date": date, "signal_date": signal_date, "holding": holding or "CASH", "momentum": float(returns.max()), "turnover": turnover})
        curve.append(equity)
    equity_curve = pd.Series(curve, index=dates, name="equity")
    metrics = calculate_performance(equity_curve, pd.DataFrame())
    metrics["rebalance_count"] = float(len(decisions))
    metrics["cash_rebalances"] = float(sum(item["holding"] == "CASH" for item in decisions))
    return equity_curve, pd.DataFrame(decisions), metrics


def run_equal_weight_backtest(price_frames: dict[str, pd.DataFrame], initial_cash: float = 100_000.0, trading_cost_bps: float = 5.0) -> tuple[pd.Series, dict[str, float]]:
    """Fully invested, no-rebalance equal-weight benchmark on the common sample."""
    if not price_frames:
        raise ValueError("At least one ETF price frame is required")
    symbols = sorted(price_frames)
    dates = sorted(set.intersection(*(set(frame.index) for frame in price_frames.values())))
    if len(dates) < 2:
        raise ValueError("At least two common price observations are required")
    prices = pd.DataFrame({symbol: price_frames[symbol].loc[dates, "adjusted_close"] for symbol in symbols}, index=dates)
    daily_returns = prices.pct_change().fillna(0.0).mean(axis=1)
    equity_curve = (1 + daily_returns).cumprod() * initial_cash * (1 - trading_cost_bps / 10_000)
    equity_curve.name = "equity"
    return equity_curve, calculate_performance(equity_curve, pd.DataFrame())


def run_risk_targeted_dual_momentum_backtest(price_frames: dict[str, pd.DataFrame], config: RiskTargetedDualMomentumConfig = RiskTargetedDualMomentumConfig()) -> tuple[pd.Series, pd.DataFrame, dict[str, float]]:
    """Dual momentum with a fixed, unlevered volatility budget and cash sleeve."""
    if not price_frames:
        raise ValueError("At least one ETF price frame is required")
    symbols = sorted(price_frames)
    dates = sorted(set.intersection(*(set(frame.index) for frame in price_frames.values())))
    minimum_history = max(config.lookback_days, config.volatility_lookback_days) + 1
    if len(dates) <= minimum_history:
        raise ValueError("Insufficient common history for risk-targeted dual momentum")
    prices = pd.DataFrame({symbol: price_frames[symbol].loc[dates, "adjusted_close"] for symbol in symbols}, index=dates)
    returns = prices.pct_change()
    equity, holding, exposure, curve, decisions = config.initial_cash, None, 0.0, [], []
    for i, date in enumerate(dates):
        if i > 0 and holding is not None:
            equity *= 1 + exposure * float(returns.loc[date, holding])
        if i > config.lookback_days and (i - config.lookback_days - 1) % config.rebalance_days == 0:
            signal_index = i - 1
            momentum = prices.iloc[signal_index] / prices.iloc[signal_index - config.lookback_days] - 1
            selected = momentum.idxmax() if momentum.max() > 0 else None
            if selected is None:
                new_exposure, annualized_volatility = 0.0, 0.0
            else:
                annualized_volatility = float(returns[selected].iloc[signal_index - config.volatility_lookback_days + 1:signal_index + 1].std(ddof=1) * math.sqrt(252))
                new_exposure = min(1.0, config.target_annual_volatility / annualized_volatility) if annualized_volatility > 0 else 0.0
            turnover = abs(new_exposure - exposure) if selected == holding else new_exposure + exposure
            equity *= 1 - turnover * config.trading_cost_bps / 10_000
            holding, exposure = selected, new_exposure
            decisions.append({"date": date, "signal_date": dates[signal_index], "holding": holding or "CASH", "momentum": float(momentum.max()), "annualized_volatility": annualized_volatility, "exposure": exposure, "turnover": turnover})
        curve.append(equity)
    equity_curve = pd.Series(curve, index=dates, name="equity")
    metrics = calculate_performance(equity_curve, pd.DataFrame())
    metrics["rebalance_count"] = float(len(decisions))
    metrics["average_exposure"] = float(pd.DataFrame(decisions)["exposure"].mean()) if decisions else 0.0
    metrics["cash_rebalances"] = float(sum(item["holding"] == "CASH" for item in decisions))
    return equity_curve, pd.DataFrame(decisions), metrics


def run_volatility_matched_equal_weight_backtest(price_frames: dict[str, pd.DataFrame], config: RiskTargetedDualMomentumConfig = RiskTargetedDualMomentumConfig()) -> tuple[pd.Series, dict[str, float]]:
    """Monthly volatility-scaled equal-weight benchmark, with no leverage."""
    if not price_frames:
        raise ValueError("At least one ETF price frame is required")
    symbols = sorted(price_frames)
    dates = sorted(set.intersection(*(set(frame.index) for frame in price_frames.values())))
    if len(dates) <= config.volatility_lookback_days + 1:
        raise ValueError("Insufficient common history for volatility-matched benchmark")
    prices = pd.DataFrame({symbol: price_frames[symbol].loc[dates, "adjusted_close"] for symbol in symbols}, index=dates)
    basket_returns = prices.pct_change().mean(axis=1)
    equity, exposure, curve = config.initial_cash, 0.0, []
    for i, date in enumerate(dates):
        if i > 0:
            equity *= 1 + exposure * float(basket_returns.iloc[i])
        if i > config.volatility_lookback_days and (i - config.volatility_lookback_days - 1) % config.rebalance_days == 0:
            signal_returns = basket_returns.iloc[i - config.volatility_lookback_days:i]
            annualized_volatility = float(signal_returns.std(ddof=1) * math.sqrt(252))
            new_exposure = min(1.0, config.target_annual_volatility / annualized_volatility) if annualized_volatility > 0 else 0.0
            equity *= 1 - abs(new_exposure - exposure) * config.trading_cost_bps / 10_000
            exposure = new_exposure
        curve.append(equity)
    equity_curve = pd.Series(curve, index=dates, name="equity")
    return equity_curve, calculate_performance(equity_curve, pd.DataFrame())


def latest_volatility_matched_exposure(price_frames: dict[str, pd.DataFrame], config: RiskTargetedDualMomentumConfig = RiskTargetedDualMomentumConfig()) -> float:
    """Exposure selected at the last completed monthly core rebalance."""
    symbols = sorted(price_frames)
    dates = sorted(set.intersection(*(set(frame.index) for frame in price_frames.values())))
    if len(dates) <= config.volatility_lookback_days + 1:
        raise ValueError("Insufficient common history for volatility-matched benchmark")
    prices = pd.DataFrame({symbol: price_frames[symbol].loc[dates, "adjusted_close"] for symbol in symbols}, index=dates)
    returns = prices.pct_change().mean(axis=1)
    rebalance_indices = [i for i in range(len(dates)) if i > config.volatility_lookback_days and (i - config.volatility_lookback_days - 1) % config.rebalance_days == 0]
    signal_index = rebalance_indices[-1]
    annualized_volatility = float(returns.iloc[signal_index - config.volatility_lookback_days:signal_index].std(ddof=1) * math.sqrt(252))
    return min(1.0, config.target_annual_volatility / annualized_volatility) if annualized_volatility > 0 else 0.0
