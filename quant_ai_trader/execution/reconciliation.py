"""Fail-closed comparison between local portfolio state and broker positions."""
from dataclasses import dataclass
from quant_ai_trader.risk.portfolio_manager import PortfolioManager

@dataclass(frozen=True)
class ReconciliationResult:
    matched: bool
    differences: tuple[str, ...]
    ignored_external_positions: tuple[str, ...] = ()

def reconcile_positions(portfolio: PortfolioManager, broker_quantities: dict[str, int]) -> ReconciliationResult:
    local = {symbol: position.shares for symbol, position in portfolio.positions.items() if position.shares}
    broker = {symbol.upper(): quantity for symbol, quantity in broker_quantities.items() if quantity}
    symbols = sorted(set(local) | set(broker))
    differences = tuple(f"{symbol}: local={local.get(symbol, 0)}, broker={broker.get(symbol, 0)}" for symbol in symbols if local.get(symbol, 0) != broker.get(symbol, 0))
    return ReconciliationResult(not differences, differences)


def reconcile_managed_positions(portfolio: PortfolioManager, broker_quantities: dict[str, int],
                                managed_symbols: set[str]) -> ReconciliationResult:
    managed = {symbol.upper() for symbol in managed_symbols}
    scoped = {symbol: quantity for symbol, quantity in broker_quantities.items() if symbol.upper() in managed}
    external = tuple(sorted(symbol for symbol, quantity in broker_quantities.items() if quantity and symbol.upper() not in managed))
    local_outside_scope = tuple(sorted(symbol for symbol, position in portfolio.positions.items() if position.shares and symbol not in managed))
    if local_outside_scope:
        return ReconciliationResult(False, tuple(f"{symbol}: local position outside managed scope" for symbol in local_outside_scope), external)
    result = reconcile_positions(portfolio, scoped)
    return ReconciliationResult(result.matched, result.differences, external)


def quantities_from_saxo_positions(payload: dict) -> dict[str, int]:
    """Aggregate Saxo position rows without assuming one row per symbol."""
    quantities: dict[str, int] = {}
    for item in payload.get("Data", []):
        symbol = item.get("Symbol") or item.get("DisplayAndFormat", {}).get("Symbol")
        amount = item.get("Amount")
        if amount is None:
            amount = item.get("PositionBase", {}).get("Amount")
        if not symbol or amount is None:
            raise ValueError("Saxo position row is missing symbol or amount")
        numeric = float(amount)
        if not numeric.is_integer():
            raise ValueError(f"Fractional Saxo position is unsupported for {symbol}")
        quantities[symbol.upper()] = quantities.get(symbol.upper(), 0) + int(numeric)
    return quantities
