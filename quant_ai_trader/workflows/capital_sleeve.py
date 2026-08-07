"""Inspect or mark the dedicated SEK capital available to the SLV pilot."""
from __future__ import annotations
import argparse
from quant_ai_trader.config.settings import Settings
from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.workflows.slv_paper_pilot import SLEEVE_NAME

def run(mark_to_market_sek: float | None = None) -> dict[str, object]:
    repo=MarketDataRepository(Settings().database_path); repo.initialize()
    sleeve=repo.get_or_create_capital_sleeve(SLEEVE_NAME,10_000.,"SEK")
    return repo.mark_capital_sleeve(SLEEVE_NAME,mark_to_market_sek) if mark_to_market_sek is not None else sleeve

if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--mark-to-market-sek",type=float); args=parser.parse_args(); print(run(args.mark_to_market_sek))
