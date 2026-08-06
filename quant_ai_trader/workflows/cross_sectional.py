"""Run and record the regime-aware cross-sectional ETF strategy."""
from __future__ import annotations
import argparse
from datetime import UTC, datetime
from uuid import uuid4
from quant_ai_trader.backtesting.cross_sectional import run_cross_sectional_backtest
from quant_ai_trader.config.settings import Settings
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.features.feature_pipeline import build_feature_dataset
from quant_ai_trader.observability.logging import configure_logging

def run(symbols: list[str], strategy_name: str = "regime_cross_sectional_v2_defensive") -> dict[str, float]:
    settings = Settings(); repo = MarketDataRepository(settings.database_path); repo.initialize()
    spy = repo.load_bars("SPY")
    frames = {symbol.upper(): build_feature_dataset(repo.load_bars(symbol.upper()), spy_bars=spy) for symbol in symbols}
    curve, rebalances, metrics = run_cross_sectional_backtest(frames)
    repo.record_strategy_run(str(uuid4()), strategy_name, ",".join(symbols).upper(), datetime.now(UTC).isoformat(), metrics)
    configure_logging().info("cross_sectional_completed", extra={"strategy": strategy_name, "event": f"rebalances={len(rebalances)}"})
    return metrics

def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--symbols", nargs="+", required=True); parser.add_argument("--strategy-name", default="regime_cross_sectional_v2_defensive")
    args = parser.parse_args(); print(run(args.symbols, args.strategy_name))

if __name__ == "__main__": main()
