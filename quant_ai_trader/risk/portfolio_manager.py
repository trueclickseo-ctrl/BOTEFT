"""In-memory portfolio state used by research, paper trading, and live execution adapters."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PortfolioPosition:
    symbol: str
    sector: str
    shares: int
    average_entry_price: float
    market_price: float

    @property
    def market_value(self) -> float:
        return self.shares * self.market_price


class PortfolioManager:
    """Tracks cash and marked positions; validation belongs to ``RiskManager``."""

    def __init__(self, cash: float = 100_000.0) -> None:
        if cash < 0:
            raise ValueError("cash cannot be negative")
        self.cash = cash
        self.positions: dict[str, PortfolioPosition] = {}

    @property
    def equity(self) -> float:
        return self.cash + sum(position.market_value for position in self.positions.values())

    def position_value(self, symbol: str) -> float:
        position = self.positions.get(symbol.upper())
        return position.market_value if position else 0.0

    def sector_exposure(self, sector: str) -> float:
        return sum(position.market_value for position in self.positions.values() if position.sector == sector)

    def mark_price(self, symbol: str, market_price: float) -> None:
        if market_price <= 0:
            raise ValueError("market_price must be positive")
        self.positions[symbol.upper()].market_price = market_price

    def open_position(self, symbol: str, sector: str, shares: int, price: float) -> None:
        symbol = symbol.upper()
        if shares < 1 or price <= 0:
            raise ValueError("shares and price must be positive")
        cost = shares * price
        if cost > self.cash:
            raise ValueError("insufficient cash")
        existing = self.positions.get(symbol)
        if existing:
            total_shares = existing.shares + shares
            existing.average_entry_price = ((existing.average_entry_price * existing.shares) + cost) / total_shares
            existing.shares, existing.market_price = total_shares, price
        else:
            self.positions[symbol] = PortfolioPosition(symbol, sector, shares, price, price)
        self.cash -= cost

    def close_position(self, symbol: str, shares: int, price: float) -> None:
        symbol = symbol.upper()
        position = self.positions[symbol]
        if shares < 1 or shares > position.shares:
            raise ValueError("close shares must be within the open position")
        self.cash += shares * price
        position.shares -= shares
        position.market_price = price
        if position.shares == 0:
            del self.positions[symbol]
