"""Train, backtest, log, and rank one ETF research strategy from stored bars."""
from __future__ import annotations
import argparse
from datetime import UTC, datetime
from uuid import uuid4
import pandas as pd

from quant_ai_trader.config.settings import Settings
from quant_ai_trader.dashboard.data_service import run_model_backtest, run_momentum_backtest
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.data.quality import validate_daily_bars
from quant_ai_trader.features.feature_pipeline import build_feature_dataset
from quant_ai_trader.features.labels import create_target_stop_labels
from quant_ai_trader.models.model_manager import ModelManager
from quant_ai_trader.models.train_model import train_target_stop_model
from quant_ai_trader.models.model_validation import ModelQualityGate
from quant_ai_trader.observability.logging import configure_logging

def build_training_dataset(repository: MarketDataRepository, symbol: str, settings: Settings):
    bars, spy = repository.load_bars(symbol), repository.load_bars("SPY")
    if bars.empty or spy.empty: raise ValueError(f"Missing stored bars for {symbol} or SPY")
    for name, data in ((symbol, bars), ("SPY", spy)):
        report = validate_daily_bars(data)
        if not report.valid: raise ValueError(f"Data-quality rejection for {name}: {','.join(report.errors)}")
    features = build_feature_dataset(bars, spy_bars=spy)
    return create_target_stop_labels(features, settings.target_return, settings.stop_loss, settings.holding_period_days)

def build_pooled_training_dataset(repository: MarketDataRepository, symbols: list[str], settings: Settings):
    frames = []
    for symbol in symbols:
        frame = build_training_dataset(repository, symbol.upper(), settings).copy()
        frame.index = pd.MultiIndex.from_arrays([frame.index, [symbol.upper()] * len(frame)], names=["date", "symbol"])
        frames.append(frame)
    return pd.concat(frames).sort_index()

def run(symbol: str, strategy_name: str = "ai_etf_target_stop") -> dict[str, float]:
    settings, logger = Settings(), configure_logging()
    repository = MarketDataRepository(settings.database_path); repository.initialize()
    dataset = build_training_dataset(repository, symbol.upper(), settings)
    result = train_target_stop_model(dataset, settings.target_return, settings.stop_loss, settings.holding_period_days)
    approved, reason = ModelQualityGate().validate(result.artifact)
    if approved: ModelManager(settings.model_directory).save(result.artifact)
    else: logger.warning("model_promotion_rejected", extra={"strategy": strategy_name, "event": reason})
    backtest = run_model_backtest(repository, result.artifact, symbol.upper())
    repository.record_strategy_run(str(uuid4()), strategy_name, symbol.upper(), datetime.now(UTC).isoformat(), backtest.metrics)
    benchmark = run_momentum_backtest(repository, symbol.upper())
    repository.record_strategy_run(str(uuid4()), "momentum_baseline", symbol.upper(), datetime.now(UTC).isoformat(), benchmark.metrics)
    logger.info("research_cycle_completed", extra={"strategy": strategy_name, "event": "backtest_completed"})
    return {**backtest.metrics, "model_promoted": float(approved)}

def run_pooled(symbols: list[str], strategy_name: str = "ai_etf_pooled") -> dict[str, float]:
    settings = Settings(); repository = MarketDataRepository(settings.database_path); repository.initialize()
    result = train_target_stop_model(build_pooled_training_dataset(repository, symbols, settings), settings.target_return, settings.stop_loss, settings.holding_period_days)
    approved, _ = ModelQualityGate().validate(result.artifact)
    if approved: ModelManager(settings.model_directory).save(result.artifact)
    returns = []
    for symbol in symbols:
        backtest = run_model_backtest(repository, result.artifact, symbol.upper()); returns.append(backtest.metrics["total_return"])
        repository.record_strategy_run(str(uuid4()), strategy_name, symbol.upper(), datetime.now(UTC).isoformat(), backtest.metrics)
        baseline = run_momentum_backtest(repository, symbol.upper())
        repository.record_strategy_run(str(uuid4()), "momentum_baseline", symbol.upper(), datetime.now(UTC).isoformat(), baseline.metrics)
    return {**result.artifact.validation_metrics, "average_backtest_return": sum(returns) / len(returns), "model_promoted": float(approved)}

def main() -> None:
    parser = argparse.ArgumentParser(description="Train and evaluate the AI ETF strategy from stored data")
    parser.add_argument("--symbol", nargs="+", required=True); parser.add_argument("--strategy-name", default="ai_etf_target_stop")
    args = parser.parse_args(); print(run(args.symbol[0], args.strategy_name) if len(args.symbol) == 1 else run_pooled(args.symbol, args.strategy_name))

if __name__ == "__main__": main()
