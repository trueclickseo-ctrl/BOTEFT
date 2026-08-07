from pathlib import Path
from quant_ai_trader.operations.strategy_approval import STRATEGY_APPROVALS, StrategyStatus, assert_paper_approved
import pytest

def test_strategy_research_register_exists():
    text = Path("STRATEGY_RESEARCH.md").read_text(encoding="utf-8")
    assert "AI target-before-stop" in text
    assert "Momentum baseline" in text


def test_no_rejected_or_research_strategy_can_submit_paper_orders():
    assert not any(item.status is StrategyStatus.PAPER_APPROVED for item in STRATEGY_APPROVALS.values())
    with pytest.raises(PermissionError, match="rejected"):
        assert_paper_approved("atr_breakout_v1_slv")
