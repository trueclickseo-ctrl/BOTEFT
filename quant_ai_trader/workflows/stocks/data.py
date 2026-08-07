"""Fetch adjusted stock research history into an isolated database."""
from pathlib import Path

from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.data.market_data import YahooFinanceProvider
from quant_ai_trader.workflows.stocks.universe import (
    BENCHMARK_SYMBOL, HISTORY_START, US_STOCK_UNIVERSE,
)

STOCK_DATABASE = Path("data/stocks/us_adjusted.sqlite3")


def run(end="2026-08-09", database_path=STOCK_DATABASE):
    provider = YahooFinanceProvider()
    repository = MarketDataRepository(database_path)
    repository.initialize()
    coverage = {}
    for symbol in (*US_STOCK_UNIVERSE, BENCHMARK_SYMBOL):
        bars = provider.fetch_daily_bars(symbol, HISTORY_START, end)
        repository.upsert_bars(symbol, bars)
        coverage[symbol] = {
            "rows": len(bars),
            "start": str(bars.index[0].date()),
            "end": str(bars.index[-1].date()),
        }
    return coverage


if __name__ == "__main__":
    print(run())
