from pathlib import Path
from quant_ai_trader.operations.strategy_approval import STRATEGY_APPROVALS, StrategyStatus, assert_paper_approved
import pytest

def test_strategy_research_register_exists():
    text = Path("STRATEGY_RESEARCH.md").read_text(encoding="utf-8")
    assert "AI target-before-stop" in text
    assert "Momentum baseline" in text


def test_stock_research_has_an_independent_register():
    etf = Path("STRATEGY_RESEARCH.md").read_text(encoding="utf-8")
    stocks = Path("STOCK_STRATEGY_RESEARCH.md").read_text(encoding="utf-8")
    assert "stock_core_satellite_consolidated_v1" not in etf
    assert "stock_core_satellite_consolidated_v1" in stocks


def test_no_rejected_or_research_strategy_can_submit_paper_orders():
    assert not any(item.status is StrategyStatus.PAPER_APPROVED for item in STRATEGY_APPROVALS.values())
    with pytest.raises(PermissionError, match="rejected"):
        assert_paper_approved("atr_breakout_v1_slv")


def test_consolidated_candidate_remains_research_only():
    approval = STRATEGY_APPROVALS["frozen_core_v2_50_50_consolidated"]
    assert approval.status is StrategyStatus.RESEARCH_ONLY
    assert not approval.may_submit_paper_order


def test_stock_candidate_remains_research_only():
    approval = STRATEGY_APPROVALS["stock_core_satellite_consolidated_v1"]
    assert approval.status is StrategyStatus.RESEARCH_ONLY
    assert not approval.may_submit_paper_order
