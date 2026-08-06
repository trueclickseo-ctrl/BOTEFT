"""Pre-trade portfolio constraints for ETF strategy signals."""

from __future__ import annotations

from dataclasses import dataclass

from quant_ai_trader.risk.portfolio_manager import PortfolioManager
from quant_ai_trader.risk.position_sizing import PositionSize, calculate_position_size


@dataclass(frozen=True)
class RiskLimits:
    risk_per_trade: float = 0.01
    maximum_positions: int = 10
    maximum_etf_allocation: float = 0.10
    maximum_sector_exposure: float = 0.30
    minimum_risk_reward: float = 2.0


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    reason: str
    position_size: PositionSize | None = None


class RiskManager:
    def __init__(self, limits: RiskLimits = RiskLimits()) -> None:
        self.limits = limits

    def evaluate_entry(
        self,
        portfolio: PortfolioManager,
        symbol: str,
        sector: str,
        entry_price: float,
        stop_loss: float,
        target_return: float,
    ) -> RiskDecision:
        """Approve only orders satisfying position count, capital, and concentration limits."""
        if target_return / stop_loss < self.limits.minimum_risk_reward:
            return RiskDecision(False, "risk_reward_below_minimum")
        existing = portfolio.positions.get(symbol.upper())
        if existing is None and len(portfolio.positions) >= self.limits.maximum_positions:
            return RiskDecision(False, "maximum_position_count_reached")
        size = calculate_position_size(
            portfolio.equity, entry_price, stop_loss, target_return,
            self.limits.risk_per_trade, self.limits.maximum_etf_allocation,
        )
        if size.shares < 1:
            return RiskDecision(False, "position_size_rounds_to_zero", size)
        if size.notional > portfolio.cash:
            return RiskDecision(False, "insufficient_cash", size)
        prospective_equity = portfolio.equity
        prospective_etf = portfolio.position_value(symbol) + size.notional
        if prospective_etf / prospective_equity > self.limits.maximum_etf_allocation:
            return RiskDecision(False, "maximum_etf_allocation_exceeded", size)
        prospective_sector = portfolio.sector_exposure(sector) + size.notional
        if prospective_sector / prospective_equity > self.limits.maximum_sector_exposure:
            return RiskDecision(False, "maximum_sector_exposure_exceeded", size)
        return RiskDecision(True, "approved", size)
