"""Evaluate and record the RSI mean-reversion strategy."""
import argparse
from datetime import UTC, datetime
from uuid import uuid4
from quant_ai_trader.backtesting.backtester import ETFBacktester
from quant_ai_trader.config.settings import Settings
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.features.feature_pipeline import build_feature_dataset
from quant_ai_trader.strategies.mean_reversion import rsi_mean_reversion_signals

def run(symbol: str) -> dict[str, float]:
    settings = Settings(); repo = MarketDataRepository(settings.database_path)
    bars, spy = repo.load_bars(symbol), repo.load_bars("SPY")
    result = ETFBacktester().run(bars, rsi_mean_reversion_signals(build_feature_dataset(bars, spy_bars=spy)))
    repo.record_strategy_run(str(uuid4()), "rsi_mean_reversion_v1", symbol.upper(), datetime.now(UTC).isoformat(), result.metrics)
    return result.metrics

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--symbol", required=True)
    print(run(parser.parse_args().symbol))
