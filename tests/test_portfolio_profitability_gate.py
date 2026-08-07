from quant_ai_trader.backtesting.evaluation import PortfolioProfitabilityGate


def test_portfolio_profitability_gate_requires_risk_and_stress_quality():
    good = {"total_return": .20, "sharpe_ratio": .9, "maximum_drawdown": -.10}
    assert PortfolioProfitabilityGate().evaluate(good, positive_folds=3, stress_total_return=.05)[0]
    bad = {"total_return": .20, "sharpe_ratio": .3, "maximum_drawdown": -.25}
    approved, blockers = PortfolioProfitabilityGate().evaluate(bad, positive_folds=2, stress_total_return=-.01)
    assert not approved and "drawdown_exceeds_15_percent" in blockers
