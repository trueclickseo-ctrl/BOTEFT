"""Generate and risk-validate the candidate's latest allocation without orders."""
from __future__ import annotations
import argparse
from quant_ai_trader.config.settings import Settings
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.execution.allocation import validate_target_weights
from quant_ai_trader.strategies.core_satellite import latest_target_weights
from quant_ai_trader.workflows.breakout_universe import DEFAULT_UNIVERSE

SECTORS = {"SPY": "Broad Market", "QQQ": "Broad Market", "IWM": "Broad Market", "DIA": "Broad Market", "XLK": "Technology", "XLF": "Financials", "XLE": "Energy", "XLV": "Health Care", "XLI": "Industrials", "XLY": "Consumer Discretionary", "XLP": "Consumer Staples", "TLT": "Rates", "GLD": "Precious Metals", "SLV": "Precious Metals"}


def run(symbols: list[str]) -> dict[str, object]:
    repo = MarketDataRepository(Settings().database_path)
    frames = {symbol.upper(): repo.load_bars(symbol.upper()) for symbol in symbols}
    missing = [symbol for symbol, frame in frames.items() if frame.empty]
    if missing: raise ValueError(f"Missing stored bars for: {', '.join(missing)}")
    weights = latest_target_weights(frames)
    validation = validate_target_weights(weights, SECTORS)
    return {"weights": weights, "approved": validation.approved, "blockers": list(validation.blockers), "orders_created": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_UNIVERSE))
    print(run(parser.parse_args().symbols))
