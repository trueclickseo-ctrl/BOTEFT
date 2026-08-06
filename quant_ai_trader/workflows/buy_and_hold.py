"""Record a passive benchmark using the same backtest engine and costs."""
import argparse
from datetime import UTC, datetime
from uuid import uuid4
import pandas as pd
from quant_ai_trader.backtesting.performance import calculate_performance
from quant_ai_trader.config.settings import Settings
from quant_ai_trader.data.database import MarketDataRepository

def run(symbol: str):
    repo = MarketDataRepository(Settings().database_path); bars = repo.load_bars(symbol)
    if len(bars) < 2: raise ValueError("At least two bars are required")
    initial_cash, allocation, cost_bps = 100_000., .10, 2.
    entry = float(bars.iloc[1]["open"]) * (1 + cost_bps / 10_000); shares = int(initial_cash * allocation / entry)
    cash = initial_cash - shares * entry
    equity = pd.Series([initial_cash] + [cash + shares * float(price) for price in bars["close"].iloc[1:]], index=bars.index)
    metrics = calculate_performance(equity, pd.DataFrame())
    repo.record_strategy_run(str(uuid4()), "buy_and_hold", symbol.upper(), datetime.now(UTC).isoformat(), metrics)
    return metrics
if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--symbol", required=True)
    print(run(parser.parse_args().symbol))
