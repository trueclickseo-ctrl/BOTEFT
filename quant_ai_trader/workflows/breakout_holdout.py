"""Strict final-period holdout evaluation for the ATR breakout candidate."""
import argparse
from quant_ai_trader.backtesting.backtester import ETFBacktester
from quant_ai_trader.backtesting.evaluation import StrategyEvidenceGate
from quant_ai_trader.config.settings import Settings
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.features.feature_pipeline import build_feature_dataset
from quant_ai_trader.strategies.breakout import breakout_signals

def run(symbol: str, train_fraction: float = .70) -> dict[str, float]:
    settings = Settings(); repo = MarketDataRepository(settings.database_path)
    bars, spy = repo.load_bars(symbol), repo.load_bars("SPY")
    features = build_feature_dataset(bars, spy_bars=spy); signals = breakout_signals(features)
    split = int(len(bars) * train_fraction)
    result = ETFBacktester().run(bars.iloc[split:], signals.iloc[split:])
    return result.metrics | {"evidence": StrategyEvidenceGate().evaluate(result.metrics)[1], "holdout_start": str(bars.index[split].date())}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--symbol", required=True)
    print(run(parser.parse_args().symbol))
