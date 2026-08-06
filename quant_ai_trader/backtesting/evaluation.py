"""Minimum-evidence gates for strategy research outcomes."""
from dataclasses import dataclass

@dataclass(frozen=True)
class StrategyEvidenceGate:
    minimum_trades: int = 30
    minimum_sharpe: float = .5
    maximum_drawdown: float = -.20
    def evaluate(self, metrics: dict[str, float]) -> tuple[bool, str]:
        if metrics.get("number_of_trades", 0) < self.minimum_trades: return False, "insufficient_trade_count"
        if metrics.get("sharpe_ratio", 0) < self.minimum_sharpe: return False, "sharpe_below_threshold"
        if metrics.get("maximum_drawdown", 0) < self.maximum_drawdown: return False, "drawdown_exceeds_limit"
        return True, "candidate"
