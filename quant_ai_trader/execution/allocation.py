"""Validate strategy allocation plans before turning them into broker orders."""
from __future__ import annotations
from dataclasses import dataclass
from quant_ai_trader.risk.risk_manager import RiskLimits


@dataclass(frozen=True)
class AllocationValidation:
    approved: bool
    blockers: tuple[str, ...]


def validate_target_weights(weights: dict[str, float], sectors: dict[str, str], limits: RiskLimits = RiskLimits()) -> AllocationValidation:
    blockers: list[str] = []
    if any(weight < 0 for weight in weights.values()): blockers.append("negative target weight")
    invested = sum(weight for symbol, weight in weights.items() if symbol != "CASH")
    if invested > 1 + 1e-9: blockers.append("target weights exceed 100%")
    for symbol, weight in weights.items():
        if symbol != "CASH" and weight > limits.maximum_etf_allocation + 1e-9:
            blockers.append(f"{symbol}: maximum ETF allocation exceeded")
    sector_weights: dict[str, float] = {}
    for symbol, weight in weights.items():
        if symbol != "CASH": sector_weights[sectors.get(symbol, "Unclassified")] = sector_weights.get(sectors.get(symbol, "Unclassified"), 0.0) + weight
    for sector, weight in sector_weights.items():
        if weight > limits.maximum_sector_exposure + 1e-9: blockers.append(f"{sector}: maximum sector exposure exceeded")
    return AllocationValidation(not blockers, tuple(blockers))
