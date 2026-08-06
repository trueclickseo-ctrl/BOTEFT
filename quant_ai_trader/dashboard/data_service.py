"""Read-only composition of stored data, trained models, and research results."""

from __future__ import annotations

import pandas as pd

from quant_ai_trader.backtesting.backtester import BacktestResult, ETFBacktester
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.features.feature_pipeline import build_feature_dataset
from quant_ai_trader.models.model_manager import ModelArtifact
from quant_ai_trader.models.predict import predict_opportunity, predict_probabilities
from quant_ai_trader.strategies.etf_strategy import StrategyRules, generate_signals
from quant_ai_trader.strategies.baselines import momentum_baseline_signals


def build_rankings(repository: MarketDataRepository, artifact: ModelArtifact) -> pd.DataFrame:
    """Return latest valid prediction for every stored non-context symbol."""
    spy = repository.load_bars("SPY")
    if spy.empty:
        raise ValueError("SPY bars are required to compute market-context features")
    rows: list[dict[str, object]] = []
    for symbol in repository.list_symbols():
        if symbol == "SPY":
            continue
        features = build_feature_dataset(repository.load_bars(symbol), spy_bars=spy)
        try:
            prediction = predict_opportunity(artifact, features)
        except ValueError:
            continue  # A symbol without sufficient history is not rankable.
        rows.append({
            "symbol": symbol, "as_of": features.index[-1], "buy_probability": prediction.buy_probability,
            "expected_return": prediction.expected_return, "decision": prediction.decision,
            "close": float(features.iloc[-1]["adjusted_close"]),
        })
    return pd.DataFrame(rows).sort_values("buy_probability", ascending=False, ignore_index=True) if rows else pd.DataFrame(
        columns=["symbol", "as_of", "buy_probability", "expected_return", "decision", "close"]
    )


def run_model_backtest(repository: MarketDataRepository, artifact: ModelArtifact, symbol: str) -> BacktestResult:
    """Backtest stored history using predictions available on each session."""
    bars, spy = repository.load_bars(symbol), repository.load_bars("SPY")
    if bars.empty or spy.empty:
        raise ValueError(f"Missing bars for {symbol} or SPY market context")
    features = build_feature_dataset(bars, spy_bars=spy)
    features["buy_probability"] = predict_probabilities(artifact, features)
    rules = StrategyRules(target_return=artifact.target_return, stop_loss=artifact.stop_loss, maximum_holding_days=artifact.holding_period_days)
    signals = generate_signals(features, rules)
    return ETFBacktester(rules).run(bars, signals)

def run_momentum_backtest(repository: MarketDataRepository, symbol: str) -> BacktestResult:
    bars, spy = repository.load_bars(symbol), repository.load_bars("SPY")
    if bars.empty or spy.empty: raise ValueError(f"Missing bars for {symbol} or SPY market context")
    features = build_feature_dataset(bars, spy_bars=spy)
    return ETFBacktester().run(bars, momentum_baseline_signals(features))
