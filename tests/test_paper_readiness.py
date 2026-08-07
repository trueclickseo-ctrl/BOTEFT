from quant_ai_trader.execution.readiness import assess_paper_readiness
from quant_ai_trader.execution.reconciliation import ReconciliationResult
from quant_ai_trader.execution.safety import TradingSafety


def test_paper_readiness_fails_closed_until_every_check_passes(tmp_path):
    safety = TradingSafety(tmp_path / "KILL_SWITCH")
    blocked = assess_paper_readiness(operator_approved=False, strategy_approved=False, account_key=None, environment="sim", safety=safety, reconciliation=ReconciliationResult(False, ("mismatch",)), allocation_translator_ready=False)
    assert not blocked.ready and len(blocked.blockers) == 5
    ready = assess_paper_readiness(operator_approved=True, strategy_approved=True, account_key="abc", environment="sim", safety=safety, reconciliation=ReconciliationResult(True, ()), allocation_translator_ready=True)
    assert ready.ready
