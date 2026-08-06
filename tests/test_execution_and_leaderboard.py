from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.execution.broker_interface import OrderRequest
from quant_ai_trader.execution.paper_trading import PaperBroker

def test_paper_broker_and_strategy_leaderboard(tmp_path):
    order = OrderRequest("SPY", 1, "Etf", "account", "Buy", 10, "ai_etf")
    assert PaperBroker().place(order)["status"] == "Filled"
    repo = MarketDataRepository(tmp_path / "db.sqlite"); repo.initialize()
    repo.record_strategy_run("1", "ai_etf", "SPY", "2026-01-01T00:00:00Z", {"total_return": .1, "sharpe_ratio": 1.2})
    assert repo.strategy_leaderboard().iloc[0]["strategy_name"] == "ai_etf"
