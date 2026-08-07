"""Preregistered literature-based long/cash stock momentum strategy."""
from dataclasses import dataclass
import math
import pandas as pd


@dataclass(frozen=True)
class LiteratureMomentumConfig:
    lookback_days: int = 252
    skip_recent_days: int = 21
    rebalance_days: int = 21
    top_n: int = 5
    volatility_lookback_days: int = 60
    market_trend_days: int = 200
    target_annual_volatility: float = .10
    maximum_stock_weight: float = .10


def build_literature_momentum_weights(prices, benchmark, config=LiteratureMomentumConfig()):
    dates = prices.index.intersection(benchmark.index)
    prices, benchmark = prices.loc[dates].astype(float), benchmark.loc[dates].astype(float)
    returns = prices.pct_change(fill_method=None)
    output = pd.DataFrame(0.0, index=dates, columns=prices.columns)
    current = pd.Series(0.0, index=prices.columns)
    required = max(config.lookback_days + config.skip_recent_days, config.market_trend_days)
    for i, date in enumerate(dates):
        output.loc[date] = current
        if i > required and (i - required - 1) % config.rebalance_days == 0:
            signal = i - 1
            current = pd.Series(0.0, index=prices.columns)
            market_ma = benchmark.iloc[signal-config.market_trend_days+1:signal+1].mean()
            if benchmark.iloc[signal] <= market_ma:
                continue
            momentum_end = signal - config.skip_recent_days
            scores = prices.iloc[momentum_end] / prices.iloc[momentum_end-config.lookback_days] - 1
            selected = scores[scores > 0].nlargest(config.top_n).index
            if selected.empty:
                continue
            vol = returns[list(selected)].iloc[signal-config.volatility_lookback_days+1:signal+1].std(ddof=1) * math.sqrt(252)
            inverse = (1 / vol.replace(0, float("nan"))).dropna()
            raw = inverse / inverse.sum()
            covariance = returns[list(raw.index)].iloc[signal-config.volatility_lookback_days+1:signal+1].cov() * 252
            portfolio_vol = float(math.sqrt(max(raw @ covariance @ raw, 0)))
            scale = min(1.0, config.target_annual_volatility / portfolio_vol) if portfolio_vol > 0 else 0.0
            current.loc[raw.index] = (raw * scale).clip(upper=config.maximum_stock_weight)
    return output
