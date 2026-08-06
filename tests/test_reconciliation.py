from quant_ai_trader.execution.reconciliation import reconcile_positions
from quant_ai_trader.risk.portfolio_manager import PortfolioManager

def test_reconciliation_detects_broker_mismatch():
    portfolio = PortfolioManager(); portfolio.open_position("SPY", "Index", 10, 100)
    assert reconcile_positions(portfolio, {"SPY": 10}).matched
    result = reconcile_positions(portfolio, {"SPY": 9, "QQQ": 1})
    assert not result.matched and len(result.differences) == 2
