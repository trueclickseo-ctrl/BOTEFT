"""Phase 1 command-line entry point for data collection and feature generation."""

from __future__ import annotations

import argparse
import pandas as pd

from quant_ai_trader.config.settings import SaxoSettings, Settings
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.data.market_data import SaxoBankProvider, SaxoInstrument, YahooFinanceProvider, sync_symbol
from quant_ai_trader.features.feature_pipeline import build_feature_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Quant AI Trader Phase 1")
    parser.add_argument("--start", required=True, help="Inclusive start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="Exclusive end date (YYYY-MM-DD)")
    parser.add_argument("--symbols", nargs="+", help="Symbols to sync; defaults to ETF universe")
    parser.add_argument("--provider", choices=("saxo", "yahoo"), default="saxo", help="Market-data source (default: saxo)")
    parser.add_argument("--incremental", action="store_true", help="Fetch only bars after the latest stored date")
    args = parser.parse_args()

    settings = Settings()
    repository = MarketDataRepository(settings.database_path)
    repository.initialize()
    if args.provider == "saxo":
        saxo = SaxoSettings.from_environment()
        instruments = {symbol: SaxoInstrument(**details) for symbol, details in saxo.instruments.items()}
        provider = SaxoBankProvider(saxo.access_token, instruments, saxo.base_url)
    else:
        provider = YahooFinanceProvider()
    symbols = args.symbols or settings.etf_universe
    for symbol in symbols:
        latest = repository.latest_bar_date(symbol) if args.incremental else None
        start = (pd.Timestamp(latest).normalize() + pd.DateOffset(days=1)).strftime("%Y-%m-%d") if latest else args.start
        if pd.Timestamp(start) >= pd.Timestamp(args.end):
            print(f"{symbol}: already up to date")
            continue
        count = sync_symbol(provider, repository, symbol, start, args.end)
        print(f"{symbol}: persisted {count} daily bars")

    # SPY is reused as market context for an example feature build.
    spy = repository.load_bars("SPY")
    for symbol in symbols:
        features = build_feature_dataset(repository.load_bars(symbol), spy_bars=spy)
        print(f"{symbol}: generated {len(features)} feature rows")


if __name__ == "__main__":
    main()
