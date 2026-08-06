from quant_ai_trader.risk.portfolio_manager import PortfolioManager
from quant_ai_trader.risk.position_sizing import calculate_position_size
from quant_ai_trader.risk.risk_manager import RiskLimits, RiskManager


def test_position_size_respects_one_percent_risk_and_ten_percent_allocation():
    size = calculate_position_size(100_000, 100, .03, .06)
    assert size.shares == 100  # $10,000 allocation cap binds before the $1,000 risk budget.
    assert size.notional == 100_000 * .10


def test_risk_manager_rejects_insufficient_reward_and_sector_concentration():
    portfolio = PortfolioManager(100_000)
    manager = RiskManager()
    assert manager.evaluate_entry(portfolio, "SPY", "Index", 100, .03, .05).reason == "risk_reward_below_minimum"
    portfolio.open_position("XLK", "Technology", 250, 100)
    limits = RiskLimits(maximum_etf_allocation=.10, maximum_sector_exposure=.30)
    decision = RiskManager(limits).evaluate_entry(portfolio, "QQQ", "Technology", 100, .03, .06)
    assert not decision.approved
    assert decision.reason == "maximum_sector_exposure_exceeded"


def test_risk_manager_approves_compliant_trade():
    decision = RiskManager().evaluate_entry(PortfolioManager(100_000), "GLD", "Commodities", 100, .03, .06)
    assert decision.approved
    assert decision.position_size is not None
