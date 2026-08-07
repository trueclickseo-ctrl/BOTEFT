"""Dependent-return robustness audit for frozen stock candidates.

This audit is deliberately rejection-only. Bootstrap evidence cannot approve a
strategy for paper trading and must not be used to tune its frozen rules.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np
import pandas as pd

from quant_ai_trader.backtesting.weight_engine import WeightEngineConfig, run_weight_backtest
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.strategies.stocks.core_satellite import build_stock_core_satellite_weights
from quant_ai_trader.strategies.stocks.literature_momentum import build_literature_momentum_weights
from quant_ai_trader.workflows.stocks.data import STOCK_DATABASE
from quant_ai_trader.workflows.stocks.large_universe_data import DATABASE as LARGE_DATABASE
from quant_ai_trader.workflows.stocks.large_universes import NASDAQ_100, SP_500_TOP_50
from quant_ai_trader.workflows.stocks.universe import US_STOCK_UNIVERSE


@dataclass(frozen=True)
class BootstrapConfig:
    samples: int = 2_000
    expected_block_days: int = 20
    seed: int = 20260807
    minimum_pass_probability: float = .95


def stationary_bootstrap_indices(length: int, expected_block_days: int, rng: np.random.Generator) -> np.ndarray:
    """Politis-Romano stationary-bootstrap indices with geometric block ends."""
    if length < 2 or expected_block_days < 1:
        raise ValueError("Bootstrap requires at least two returns and a positive block length")
    result = np.empty(length, dtype=int)
    result[0] = rng.integers(length)
    restart_probability = 1.0 / expected_block_days
    for position in range(1, length):
        if rng.random() < restart_probability:
            result[position] = rng.integers(length)
        else:
            result[position] = (result[position - 1] + 1) % length
    return result


def bootstrap_daily_returns(daily_returns: pd.Series, config: BootstrapConfig = BootstrapConfig()) -> dict:
    values = daily_returns.dropna().to_numpy(dtype=float)
    if len(values) < 252:
        raise ValueError("At least 252 net daily returns are required")
    rng = np.random.default_rng(config.seed)
    sharpes, drawdowns, total_returns = [], [], []
    for _ in range(config.samples):
        sampled = values[stationary_bootstrap_indices(len(values), config.expected_block_days, rng)]
        std = sampled.std(ddof=1)
        sharpes.append(float(sampled.mean() / std * math.sqrt(252)) if std > 0 else 0.0)
        equity = np.cumprod(1.0 + sampled)
        drawdowns.append(float(np.min(equity / np.maximum.accumulate(equity) - 1.0)))
        total_returns.append(float(equity[-1] - 1.0))
    sharpes = np.asarray(sharpes); drawdowns = np.asarray(drawdowns); total_returns = np.asarray(total_returns)
    sharpe_pass_probability = float(np.mean(sharpes >= .75))
    drawdown_pass_probability = float(np.mean(drawdowns >= -.15))
    joint_pass_probability = float(np.mean((sharpes >= .75) & (drawdowns >= -.15) & (total_returns > 0)))
    robust = joint_pass_probability >= config.minimum_pass_probability
    return {
        "samples": config.samples,
        "expected_block_days": config.expected_block_days,
        "sharpe_5pct": float(np.quantile(sharpes, .05)),
        "sharpe_median": float(np.median(sharpes)),
        "drawdown_5pct": float(np.quantile(drawdowns, .05)),
        "drawdown_median": float(np.median(drawdowns)),
        "total_return_5pct": float(np.quantile(total_returns, .05)),
        "sharpe_pass_probability": sharpe_pass_probability,
        "drawdown_pass_probability": drawdown_pass_probability,
        "joint_gate_pass_probability": joint_pass_probability,
        "robustness_gate_pass": robust,
        "paper_approved": False,
    }


def _net_returns(prices: pd.DataFrame, weights: pd.DataFrame) -> pd.Series:
    curve, _, _ = run_weight_backtest(prices, weights, WeightEngineConfig())
    return curve.pct_change(fill_method=None).dropna()


def _core_satellite_returns(repository: MarketDataRepository) -> pd.Series:
    frames = {symbol: repository.load_bars(symbol) for symbol in US_STOCK_UNIVERSE}
    dates = sorted(set.intersection(*(set(frame.index) for frame in frames.values())))
    prices = pd.DataFrame({symbol: frames[symbol].loc[dates, "adjusted_close"] for symbol in US_STOCK_UNIVERSE}, index=dates)
    weights, _ = build_stock_core_satellite_weights(prices)
    return _net_returns(prices, weights)


def _momentum_returns(repository: MarketDataRepository, universe: tuple[str, ...]) -> pd.Series:
    benchmark = repository.load_bars("SPY")["adjusted_close"]
    prices = pd.DataFrame({symbol: repository.load_bars(symbol)["adjusted_close"].reindex(benchmark.index) for symbol in universe})
    weights = build_literature_momentum_weights(prices, benchmark)
    return _net_returns(prices, weights)


def run(stock_database=STOCK_DATABASE, large_database=LARGE_DATABASE, config: BootstrapConfig = BootstrapConfig()):
    stock_repository = MarketDataRepository(stock_database)
    large_repository = MarketDataRepository(large_database)
    return {
        "method": "stationary bootstrap of canonical net-of-cost daily portfolio returns",
        "approval_authority": "rejection-only",
        "stock_core_satellite_consolidated_v1": bootstrap_daily_returns(_core_satellite_returns(stock_repository), config),
        "stock_literature_momentum_v1_nasdaq_100": bootstrap_daily_returns(_momentum_returns(large_repository, NASDAQ_100), config),
        "stock_literature_momentum_v1_sp_500_top_50": bootstrap_daily_returns(_momentum_returns(large_repository, SP_500_TOP_50), config),
    }


if __name__ == "__main__":
    print(run())
