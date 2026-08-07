"""Hard-cap diversified core-satellite portfolio backtest."""
from __future__ import annotations
from dataclasses import dataclass
import math
import pandas as pd
from quant_ai_trader.backtesting.performance import calculate_performance

SECTORS = {"SPY":"Broad Market","QQQ":"Broad Market","IWM":"Broad Market","DIA":"Broad Market","XLK":"Technology","XLF":"Financials","XLE":"Energy","XLV":"Health Care","XLI":"Industrials","XLY":"Consumer Discretionary","XLP":"Consumer Staples","TLT":"Rates","GLD":"Precious Metals","SLV":"Precious Metals"}

@dataclass(frozen=True)
class DiversifiedCoreSatelliteConfig:
    initial_cash: float = 100_000.0
    lookback_days: int = 252
    volatility_lookback_days: int = 20
    rebalance_days: int = 21
    target_annual_volatility: float = .10
    core_weight: float = .5
    top_n: int = 8
    maximum_etf_allocation: float = .10
    maximum_sector_exposure: float = .30
    trading_cost_bps: float = 5.0


def run_diversified_core_satellite_backtest(frames: dict[str, pd.DataFrame], config: DiversifiedCoreSatelliteConfig = DiversifiedCoreSatelliteConfig()):
    symbols = sorted(frames); dates = sorted(set.intersection(*(set(frame.index) for frame in frames.values())))
    if len(dates) <= config.lookback_days + 1: raise ValueError("Insufficient common history")
    prices = pd.DataFrame({symbol: frames[symbol].loc[dates, "adjusted_close"] for symbol in symbols}, index=dates)
    returns, basket_returns = prices.pct_change(), prices.pct_change().mean(axis=1)
    equity, weights, curve, log = config.initial_cash, {}, [], []
    for i, date in enumerate(dates):
        if i: equity *= 1 + sum(weights.get(symbol, 0) * float(returns.loc[date, symbol]) for symbol in symbols)
        if i > config.lookback_days and (i - config.lookback_days - 1) % config.rebalance_days == 0:
            core_vol = float(basket_returns.iloc[i-config.volatility_lookback_days:i].std(ddof=1) * math.sqrt(252))
            core_exposure = min(1., config.target_annual_volatility / core_vol) if core_vol > 0 else 0.
            target = {symbol: config.core_weight * core_exposure / len(symbols) for symbol in symbols}
            sector_totals = {sector: 0. for sector in set(SECTORS.values())}
            for symbol, weight in target.items(): sector_totals[SECTORS.get(symbol, "Unclassified")] = sector_totals.get(SECTORS.get(symbol, "Unclassified"), 0.) + weight
            momentum = prices.iloc[i-1] / prices.iloc[i-1-config.lookback_days] - 1
            candidates = [symbol for symbol in momentum.sort_values(ascending=False).index if momentum[symbol] > 0][:config.top_n]
            candidate_returns = returns[candidates].iloc[i-config.volatility_lookback_days:i].mean(axis=1) if candidates else pd.Series(dtype=float)
            satellite_vol = float(candidate_returns.std(ddof=1) * math.sqrt(252)) if not candidate_returns.empty else 0.
            satellite_budget = (1-config.core_weight) * min(1., config.target_annual_volatility / satellite_vol) if satellite_vol > 0 else 0.
            unit = satellite_budget / config.top_n
            selected = []
            for symbol in candidates:
                sector = SECTORS.get(symbol, "Unclassified")
                if target[symbol] + unit <= config.maximum_etf_allocation + 1e-12 and sector_totals.get(sector, 0.) + unit <= config.maximum_sector_exposure + 1e-12:
                    target[symbol] += unit; sector_totals[sector] = sector_totals.get(sector, 0.) + unit; selected.append(symbol)
            turnover = sum(abs(target.get(s, 0.) - weights.get(s, 0.)) for s in set(target) | set(weights))
            equity *= 1 - turnover * config.trading_cost_bps / 10_000
            weights = target
            log.append({"date":date,"selected":",".join(selected),"invested":sum(weights.values()),"turnover":turnover,"maximum_etf_weight":max(weights.values(), default=0.),"maximum_sector_weight":max(sector_totals.values(), default=0.)})
        curve.append(equity)
    series = pd.Series(curve, index=dates, name="equity")
    return series, pd.DataFrame(log), calculate_performance(series, pd.DataFrame())
