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


@dataclass(frozen=True)
class ProfitabilityGate:
    minimum_trades: int = 30
    minimum_sharpe: float = .75
    minimum_profit_factor: float = 1.25
    maximum_drawdown: float = -.15
    minimum_fold_wins: int = 3

    def evaluate(self, metrics: dict[str, float], *, fold_wins: int, stress_total_return: float) -> tuple[bool, tuple[str, ...]]:
        blockers: list[str] = []
        if metrics.get("number_of_trades", 0) < self.minimum_trades: blockers.append("insufficient_trade_count")
        if metrics.get("total_return", 0) <= 0: blockers.append("net_return_not_positive")
        if metrics.get("average_net_profit", 0) <= 0: blockers.append("expectancy_not_positive")
        if metrics.get("profit_factor", 0) < self.minimum_profit_factor: blockers.append("profit_factor_below_1_25")
        if metrics.get("sharpe_ratio", 0) < self.minimum_sharpe: blockers.append("sharpe_below_0_75")
        if metrics.get("maximum_drawdown", 0) < self.maximum_drawdown: blockers.append("drawdown_exceeds_15_percent")
        if fold_wins < self.minimum_fold_wins: blockers.append("fewer_than_3_of_4_fold_wins")
        if stress_total_return <= 0: blockers.append("fails_doubled_cost_stress")
        return not blockers, tuple(blockers)


@dataclass(frozen=True)
class PortfolioProfitabilityGate:
    minimum_sharpe: float = .75
    maximum_drawdown: float = -.15
    minimum_positive_folds: int = 3

    def evaluate(self, metrics: dict[str, float], *, positive_folds: int, stress_total_return: float) -> tuple[bool, tuple[str, ...]]:
        blockers: list[str] = []
        if metrics.get("total_return", 0) <= 0: blockers.append("net_return_not_positive")
        if metrics.get("sharpe_ratio", 0) < self.minimum_sharpe: blockers.append("sharpe_below_0_75")
        if metrics.get("maximum_drawdown", 0) < self.maximum_drawdown: blockers.append("drawdown_exceeds_15_percent")
        if positive_folds < self.minimum_positive_folds: blockers.append("fewer_than_3_of_4_positive_folds")
        if stress_total_return <= 0: blockers.append("fails_doubled_cost_stress")
        return not blockers, tuple(blockers)
