from quant_ai_trader.data.database import MarketDataRepository

def test_strategy_history_expands_saved_metrics(tmp_path):
    repo = MarketDataRepository(tmp_path / "db.sqlite"); repo.initialize()
    repo.record_strategy_run("run", "test", "QQQ", "2026-01-01T00:00:00Z", {"sharpe_ratio": 1.2, "number_of_trades": 10})
    history = repo.strategy_history()
    assert history.iloc[0]["sharpe_ratio"] == 1.2
