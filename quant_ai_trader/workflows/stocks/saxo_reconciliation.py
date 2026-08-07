"""Read-only reconciliation of BOTEF-managed stocks against Saxo SIM."""
from __future__ import annotations

import json
import os
from pathlib import Path
from dotenv import load_dotenv

from quant_ai_trader.config.settings import SaxoSettings
from quant_ai_trader.execution.broker_interface import SaxoBroker
from quant_ai_trader.execution.reconciliation import quantities_from_saxo_positions
from quant_ai_trader.workflows.stocks.universe import US_STOCK_UNIVERSE


LOCAL_LEDGER = Path("runtime/stock_positions.json")


def _local_quantities(path: Path) -> tuple[dict[str, int] | None, dict[str, int]]:
    if not path.exists():
        return None, {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    quantities = payload.get("quantities")
    if not isinstance(quantities, dict):
        raise ValueError("Local stock ledger must contain a quantities object")
    baseline = payload.get("external_baseline", {})
    if not isinstance(baseline, dict):
        raise ValueError("Local stock ledger external_baseline must be an object")
    return ({symbol.upper(): int(quantity) for symbol, quantity in quantities.items() if int(quantity)},
            {symbol.upper(): int(quantity) for symbol, quantity in baseline.items() if int(quantity)})


def compare_snapshots(broker_quantities: dict[str, int], local_quantities: dict[str, int] | None,
                      external_baseline: dict[str, int] | None = None) -> dict:
    managed = set(US_STOCK_UNIVERSE)
    baseline = {symbol.upper(): int(quantity) for symbol, quantity in (external_baseline or {}).items()}
    broker_managed = {symbol: quantity - baseline.get(symbol, 0)
                      for symbol, quantity in broker_quantities.items() if symbol in managed}
    broker_managed = {symbol: quantity for symbol, quantity in broker_managed.items() if quantity}
    external = sorted(symbol for symbol, quantity in broker_quantities.items()
                      if symbol not in managed and quantity)
    if local_quantities is None:
        differences = [] if not broker_managed else [
            f"{symbol}: local ledger missing, broker={quantity}"
            for symbol, quantity in sorted(broker_managed.items())
        ]
        local_state = "implicit_flat_verified" if not differences else "missing_with_broker_positions"
    else:
        local_managed = {symbol: quantity for symbol, quantity in local_quantities.items()
                         if symbol in managed and quantity}
        symbols = sorted(set(local_managed) | set(broker_managed))
        differences = [f"{symbol}: local={local_managed.get(symbol, 0)}, broker={broker_managed.get(symbol, 0)}"
                       for symbol in symbols if local_managed.get(symbol, 0) != broker_managed.get(symbol, 0)]
        local_state = "loaded"
    return {"matched": not differences, "differences": differences,
            "broker_managed_quantities": broker_managed,
            "ignored_external_positions": external, "local_state": local_state}


def run(ledger_path: Path = LOCAL_LEDGER) -> dict:
    """Fetch positions only; never precheck, place, change, or cancel an order."""
    load_dotenv(dotenv_path=Path(".env"))
    settings = SaxoSettings.from_environment()
    account_key = os.getenv("SAXO_ACCOUNT_KEY")
    if not account_key:
        raise RuntimeError("SAXO_ACCOUNT_KEY is required")
    broker = SaxoBroker(settings.access_token, settings.base_url, environment=settings.environment)
    payload = broker.positions(account_key, os.getenv("SAXO_CLIENT_KEY"))
    broker_quantities = quantities_from_saxo_positions(payload)
    local, baseline = _local_quantities(ledger_path)
    result = compare_snapshots(broker_quantities, local, baseline)
    result.update({"environment": settings.environment, "read_only": True,
                   "broker_position_rows": len(payload.get("Data", [])),
                   "external_baseline": baseline})
    return result


if __name__ == "__main__":
    print(run())
