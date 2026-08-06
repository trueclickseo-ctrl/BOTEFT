from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.workflows.cross_sectional import run

def test_cross_sectional_workflow_records_result(tmp_path, sample_bars, monkeypatch):
    monkeypatch.chdir(tmp_path); repo = MarketDataRepository("data/quant_ai_trader.sqlite3"); repo.initialize()
    for symbol in ("SPY", "QQQ", "IWM"): repo.upsert_bars(symbol, sample_bars)
    run(["QQQ", "IWM"])
    assert not repo.strategy_leaderboard().empty
