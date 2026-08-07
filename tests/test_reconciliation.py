from quant_ai_trader.execution.reconciliation import reconcile_positions, reconcile_managed_positions, quantities_from_saxo_positions
from quant_ai_trader.risk.portfolio_manager import PortfolioManager

def test_reconciliation_detects_broker_mismatch():
    portfolio = PortfolioManager(); portfolio.open_position("SPY", "Index", 10, 100)
    assert reconcile_positions(portfolio, {"SPY": 10}).matched
    result = reconcile_positions(portfolio, {"SPY": 9, "QQQ": 1})
    assert not result.matched and len(result.differences) == 2


def test_saxo_position_rows_are_aggregated_for_reconciliation():
    payload = {"Data": [
        {"DisplayAndFormat": {"Symbol": "SPY"}, "PositionBase": {"Amount": 4}},
        {"DisplayAndFormat": {"Symbol": "SPY"}, "PositionBase": {"Amount": 6}},
    ]}
    assert quantities_from_saxo_positions(payload) == {"SPY": 10}


def test_reconciliation_ignores_but_reports_positions_outside_botef_scope():
    result = reconcile_managed_positions(PortfolioManager(), {"AAPL": 5}, {"SPY", "SLV"})
    assert result.matched
    assert result.ignored_external_positions == ("AAPL",)
