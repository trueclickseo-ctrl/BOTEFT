"""Resolve Saxo UICs for a controlled universe before syncing data."""
from __future__ import annotations
import argparse, json
import requests
from quant_ai_trader.config.settings import SaxoSettings

def lookup(symbols: list[str], settings: SaxoSettings) -> dict[str, dict[str, int | str]]:
    session = requests.Session(); session.headers.update({"Authorization": f"Bearer {settings.access_token}"})
    resolved = {}
    for symbol in symbols:
        response = session.get(f"{settings.base_url}/ref/v1/instruments", params={"AssetTypes": "Etf", "Keywords": symbol, "$top": 20}, timeout=30)
        response.raise_for_status()
        matches = [item for item in response.json().get("Data", []) if item.get("Symbol", "").split(":")[0].upper() == symbol.upper()]
        if not matches: raise ValueError(f"No exact ETF match returned for {symbol}")
        # Prefer a US venue when available; operator must still verify the listing.
        choice = next((item for item in matches if item.get("Symbol", "").endswith((":arcx", ":xnas"))), matches[0])
        resolved[symbol.upper()] = {"uic": int(choice["Identifier"]), "asset_type": choice["AssetType"]}
    return resolved

def main() -> None:
    parser = argparse.ArgumentParser(description="Look up Saxo ETF UIC mappings")
    parser.add_argument("symbols", nargs="+"); args = parser.parse_args()
    print(json.dumps(lookup(args.symbols, SaxoSettings.from_environment()), separators=(",", ":")))

if __name__ == "__main__": main()
