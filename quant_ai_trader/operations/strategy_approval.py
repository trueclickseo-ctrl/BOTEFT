"""Machine-enforced strategy eligibility derived from the research register."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class StrategyStatus(StrEnum):
    RESEARCH_ONLY = "research_only"
    REJECTED = "rejected"
    PAPER_APPROVED = "paper_approved"


@dataclass(frozen=True)
class StrategyApproval:
    strategy: str
    status: StrategyStatus
    reason: str

    @property
    def may_submit_paper_order(self) -> bool:
        return self.status is StrategyStatus.PAPER_APPROVED


STRATEGY_APPROVALS: dict[str, StrategyApproval] = {
    "atr_breakout_v1_slv": StrategyApproval(
        "atr_breakout_v1_slv", StrategyStatus.REJECTED,
        "Full-universe review found that SLV trailed its passive return mandate.",
    ),
    "risk_targeted_dual_momentum_v1": StrategyApproval(
        "risk_targeted_dual_momentum_v1", StrategyStatus.RESEARCH_ONLY,
        "Unseen consistency gate passed in only two of four folds.",
    ),
    "core_satellite_v1": StrategyApproval(
        "core_satellite_v1", StrategyStatus.REJECTED,
        "Latest allocation breached the ten-percent per-ETF cap.",
    ),
    "defensive_momentum_v1": StrategyApproval(
        "defensive_momentum_v1", StrategyStatus.REJECTED,
        "Drawdown and cost stress passed, but exact-cost Sharpe was only 0.32.",
    ),
    "defensive_momentum_v2_broad": StrategyApproval(
        "defensive_momentum_v2_broad", StrategyStatus.REJECTED,
        "Exact-cost Sharpe was 0.62 and the redesign requires genuinely unseen confirmation.",
    ),
    "defensive_momentum_v2_weekly_vol_overlay": StrategyApproval(
        "defensive_momentum_v2_weekly_vol_overlay", StrategyStatus.REJECTED,
        "Weekly thresholded resizing reduced exact-cost Sharpe to 0.51.",
    ),
}


def approval_for(strategy: str) -> StrategyApproval:
    return STRATEGY_APPROVALS.get(
        strategy,
        StrategyApproval(strategy, StrategyStatus.RESEARCH_ONLY, "Strategy has no explicit paper approval record."),
    )


def assert_paper_approved(strategy: str) -> None:
    approval = approval_for(strategy)
    if not approval.may_submit_paper_order:
        raise PermissionError(f"{strategy} is {approval.status}: {approval.reason}")
