"""Fail-closed comparison between local portfolio state and broker positions."""
from dataclasses import dataclass
from quant_ai_trader.risk.portfolio_manager import PortfolioManager

@dataclass(frozen=True)
class ReconciliationResult:
    matched: bool
    differences: tuple[str, ...]

def reconcile_positions(portfolio: PortfolioManager, broker_quantities: dict[str, int]) -> ReconciliationResult:
    local = {symbol: position.shares for symbol, position in portfolio.positions.items() if position.shares}
    broker = {symbol.upper(): quantity for symbol, quantity in broker_quantities.items() if quantity}
    symbols = sorted(set(local) | set(broker))
    differences = tuple(f"{symbol}: local={local.get(symbol, 0)}, broker={broker.get(symbol, 0)}" for symbol in symbols if local.get(symbol, 0) != broker.get(symbol, 0))
    return ReconciliationResult(not differences, differences)
